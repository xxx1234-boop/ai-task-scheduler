from typing import List, Optional

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Task, TaskUpdate
from app.services.base import BaseCRUDService


class TaskService(BaseCRUDService[Task, TaskUpdate]):
    """Extended task service with custom query methods."""

    async def get_all_with_filters(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        project_id: Optional[int] = None,
        genre_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        has_parent: Optional[bool] = None,
        parent_task_id: Optional[int] = None,
        sort: Optional[str] = None,
    ) -> tuple[List[Task], int]:
        """Get tasks with complex filtering.

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Number of records to return
            project_id: Filter by project ID
            genre_id: Filter by genre ID
            status: Filter by status
            priority: Filter by priority
            has_parent: Filter by presence of parent (True = has parent, False = no parent)
            parent_task_id: Filter by specific parent task ID
            sort: Field name to sort by (prefix with - for descending)

        Returns:
            Tuple of (items list, total count)
        """
        # Base query with relationships
        query = select(Task).options(
            selectinload(Task.project), selectinload(Task.genre)
        )

        # Apply filters
        if project_id is not None:
            query = query.where(Task.project_id == project_id)
        if genre_id is not None:
            query = query.where(Task.genre_id == genre_id)
        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if has_parent is not None:
            if has_parent:
                query = query.where(Task.parent_task_id.isnot(None))
            else:
                query = query.where(Task.parent_task_id.is_(None))
        if parent_task_id is not None:
            query = query.where(Task.parent_task_id == parent_task_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Apply sorting
        if sort:
            desc = sort.startswith("-")
            field = sort.lstrip("-")
            if hasattr(Task, field):
                order_col = getattr(Task, field)
                query = query.order_by(order_col.desc() if desc else order_col)
        else:
            # Default sort: by status (doing > todo > waiting > done) and deadline
            query = query.order_by(Task.status, Task.deadline.asc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await session.execute(query)
        items = result.scalars().all()

        return items, total

    async def get_children(
        self, session: AsyncSession, parent_id: int
    ) -> List[Task]:
        """Get all child tasks of a parent.

        Args:
            session: Database session
            parent_id: Parent task ID

        Returns:
            List of child tasks
        """
        query = select(Task).where(Task.parent_task_id == parent_id)
        result = await session.execute(query)
        return result.scalars().all()
