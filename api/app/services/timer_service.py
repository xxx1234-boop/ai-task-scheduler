from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import TimeEntry, Task
from app.exceptions import TimerNotRunningException, ValidationException, NotFoundException


class TimerService:
    """Service for timer operations."""

    async def get_running_timer(
        self, session: AsyncSession, for_update: bool = False
    ) -> Optional[TimeEntry]:
        """Get the currently running timer (end_time=NULL).

        Args:
            session: Database session
            for_update: If True, acquire row-level lock (SELECT FOR UPDATE)

        Returns:
            TimeEntry if a timer is running, None otherwise
        """
        query = select(TimeEntry).where(TimeEntry.end_time.is_(None))
        if for_update:
            query = query.with_for_update()
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def start_timer(
        self,
        session: AsyncSession,
        task_id: Optional[int] = None,
        task_name: Optional[str] = None,
    ) -> tuple[TimeEntry, Optional[TimeEntry]]:
        """Start timer for a task.

        Args:
            session: Database session
            task_id: Task ID to start timer for
            task_name: Task name to search for (alternative to task_id)

        Returns:
            Tuple of (new_entry, previous_entry if auto-stopped)

        Raises:
            ValidationException: If neither task_id nor task_name is provided
            NotFoundException: If task not found
        """
        # Find task
        if task_id:
            task = await self._get_task_by_id(session, task_id)
        elif task_name:
            task = await self._get_task_by_name(session, task_name)
        else:
            raise ValidationException("Either task_id or task_name required")

        # Stop running timer if exists (with lock to prevent race condition)
        previous_entry = None
        running = await self.get_running_timer(session, for_update=True)
        if running:
            previous_entry = await self.stop_timer(session)

        # Update task status to "doing" if not already
        if task.status != "doing":
            task.status = "doing"
            session.add(task)

        # Create new timer
        new_entry = TimeEntry(
            task_id=task.id,
            start_time=datetime.now(),
        )
        session.add(new_entry)
        await session.commit()
        await session.refresh(new_entry)

        return new_entry, previous_entry

    async def stop_timer(
        self,
        session: AsyncSession,
        note: Optional[str] = None,
    ) -> TimeEntry:
        """Stop the running timer.

        Args:
            session: Database session
            note: Optional note to add to the time entry

        Returns:
            The stopped TimeEntry

        Raises:
            TimerNotRunningException: If no timer is currently running
        """
        timer = await self.get_running_timer(session, for_update=True)
        if not timer:
            raise TimerNotRunningException()

        # Stop timer
        now = datetime.now()
        timer.end_time = now
        timer.duration_minutes = int((now - timer.start_time).total_seconds() / 60)
        if note:
            timer.note = note

        session.add(timer)

        # Note: actual_hours is now calculated dynamically from time_entries
        # No need to update task.actual_hours (column was removed)

        await session.commit()
        await session.refresh(timer)

        return timer

    async def get_timer_status(
        self, session: AsyncSession
    ) -> dict:
        """Get current timer status.

        Returns:
            Dict with is_running, current_entry, and last_entry
        """
        running = await self.get_running_timer(session)

        if running:
            # Load task relationship
            await session.refresh(running, ["task"])
            elapsed = int((datetime.now() - running.start_time).total_seconds() / 60)

            # Load project if available
            project_name = None
            if running.task.project_id:
                await session.refresh(running.task, ["project"])
                project_name = running.task.project.name if running.task.project else None

            return {
                "is_running": True,
                "current_entry": {
                    "time_entry_id": running.id,
                    "task_id": running.task_id,
                    "task_name": running.task.name,
                    "project_name": project_name,
                    "start_time": running.start_time,
                    "elapsed_minutes": elapsed,
                },
                "last_entry": None,
            }

        # Get last entry
        query = (
            select(TimeEntry)
            .where(TimeEntry.end_time.isnot(None))
            .order_by(TimeEntry.end_time.desc())
            .limit(1)
        )
        result = await session.execute(query)
        last = result.scalar_one_or_none()

        if last:
            await session.refresh(last, ["task"])

        return {
            "is_running": False,
            "current_entry": None,
            "last_entry": {
                "task_name": last.task.name if last else None,
                "end_time": last.end_time if last else None,
                "duration_minutes": last.duration_minutes if last else None,
            }
            if last
            else None,
        }

    async def _get_task_by_id(
        self, session: AsyncSession, task_id: int
    ) -> Task:
        """Get task by ID.

        Args:
            session: Database session
            task_id: Task ID

        Returns:
            Task object

        Raises:
            NotFoundException: If task not found
        """
        query = select(Task).where(Task.id == task_id)
        result = await session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise NotFoundException(f"Task with id {task_id} not found")

        return task

    async def _get_task_by_name(
        self, session: AsyncSession, task_name: str
    ) -> Task:
        """Get task by name (partial match).

        Args:
            session: Database session
            task_name: Task name to search for

        Returns:
            Task object

        Raises:
            NotFoundException: If task not found
        """
        query = select(Task).where(Task.name.ilike(f"%{task_name}%"))
        result = await session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise NotFoundException(f"Task with name '{task_name}' not found")

        return task

