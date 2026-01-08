from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlmodel import select, func, and_, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Task, Project, Genre, Schedule, TimeEntry, TaskDependency
from app.services.timer_service import TimerService
from app.schemas.dashboard import (
    TimerInfo,
    KanbanTaskItem,
    KanbanColumns,
    KanbanCounts,
    KanbanResponse,
    TodayScheduleItem,
    TodaySummary,
    TodayResponse,
    TimelineBlock,
    TimelineResponse,
    WeeklyTimelineDay,
    WeeklyTimelineResponse,
    GroupedHours,
    DailyData,
    WeeklyTotals,
    WeeklyResponse,
    GenreRatio,
    EstimationAccuracy,
    DistributionItem,
    TimeDistribution,
    CompletionRate,
    ContextSwitches,
    StatsResponse,
    TodayBasicSummary,
    WeekBasicSummary,
    UrgentSummary,
    SummaryResponse,
)


class DashboardService:
    """Service for dashboard data aggregation."""

    def __init__(self):
        self.timer_service = TimerService()

    # ===== Helper Methods =====

    def _get_week_bounds(self, target_date: Optional[date] = None) -> tuple[date, date]:
        """Get Monday and Sunday of the week containing target_date."""
        if target_date is None:
            target_date = date.today()
        # Monday = 0, Sunday = 6
        monday = target_date - timedelta(days=target_date.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday

    async def _get_timer_info(self, session: AsyncSession) -> TimerInfo:
        """Get current timer status."""
        status = await self.timer_service.get_timer_status(session)
        if status["is_running"] and status["current_entry"]:
            return TimerInfo(
                is_running=True,
                task_name=status["current_entry"]["task_name"],
                elapsed_minutes=status["current_entry"]["elapsed_minutes"],
            )
        return TimerInfo(is_running=False)

    async def _get_task_actual_hours(
        self, session: AsyncSession, task_id: int
    ) -> Decimal:
        """Get actual hours for a task from time entries."""
        query = select(func.sum(TimeEntry.duration_minutes)).where(
            TimeEntry.task_id == task_id,
            TimeEntry.duration_minutes.isnot(None),
        )
        result = await session.execute(query)
        total_minutes = result.scalar_one() or 0
        return Decimal(total_minutes) / 60

    async def _get_blocking_task_names(
        self, session: AsyncSession, task_id: int
    ) -> List[str]:
        """Get names of tasks blocking this task."""
        query = (
            select(Task.name)
            .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
            .where(
                TaskDependency.task_id == task_id,
                Task.status.notin_(["done", "archive"]),
            )
        )
        result = await session.execute(query)
        return [row[0] for row in result.all()]

    # ===== Kanban =====

    async def get_kanban(
        self, session: AsyncSession, project_id: Optional[int] = None
    ) -> KanbanResponse:
        """Get kanban board data."""
        # Get running timer's task_id
        running_timer = await self.timer_service.get_running_timer(session)
        running_task_id = running_timer.task_id if running_timer else None

        # Build base query
        query = (
            select(Task, Project.name.label("project_name"), Genre.name.label("genre_name"), Genre.color.label("genre_color"))
            .outerjoin(Project, Task.project_id == Project.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(Task.status.in_(["todo", "doing", "waiting", "done"]))
        )

        if project_id:
            query = query.where(Task.project_id == project_id)

        query = query.order_by(Task.priority.desc(), Task.deadline.asc().nullslast())

        result = await session.execute(query)
        rows = result.all()

        # Group by status
        columns = KanbanColumns()
        counts = KanbanCounts()

        for row in rows:
            task = row[0]
            actual_hours = await self._get_task_actual_hours(session, task.id)
            blocked_by = await self._get_blocking_task_names(session, task.id)

            item = KanbanTaskItem(
                id=task.id,
                name=task.name,
                description=task.description,
                project_name=row.project_name,
                genre_name=row.genre_name,
                genre_color=row.genre_color,
                priority=task.priority,
                deadline=task.deadline,
                estimated_hours=task.estimated_hours,
                actual_hours=actual_hours,
                blocked_by=blocked_by,
                is_timer_running=(task.id == running_task_id),
            )

            if task.status == "todo":
                columns.todo.append(item)
                counts.todo += 1
            elif task.status == "doing":
                columns.doing.append(item)
                counts.doing += 1
            elif task.status == "waiting":
                columns.waiting.append(item)
                counts.waiting += 1
            elif task.status == "done":
                columns.done.append(item)
                counts.done += 1

        return KanbanResponse(columns=columns, counts=counts)

    # ===== Today =====

    async def get_today(self, session: AsyncSession) -> TodayResponse:
        """Get today's schedule and summary."""
        today = date.today()
        timer = await self._get_timer_info(session)

        # Get schedules for today
        query = (
            select(
                Schedule,
                Task.name.label("task_name"),
                Project.name.label("project_name"),
                Genre.color.label("genre_color"),
            )
            .join(Task, Schedule.task_id == Task.id)
            .outerjoin(Project, Task.project_id == Project.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(func.date(Schedule.scheduled_date) == today)
            .order_by(Schedule.start_time.asc().nullslast())
        )
        result = await session.execute(query)
        rows = result.all()

        schedules = []
        planned_hours = Decimal("0")

        for row in rows:
            schedule = row[0]
            start_str = schedule.start_time.strftime("%H:%M") if schedule.start_time else None
            end_str = schedule.end_time.strftime("%H:%M") if schedule.end_time else None

            schedules.append(
                TodayScheduleItem(
                    id=schedule.id,
                    start_time=start_str,
                    end_time=end_str,
                    task_id=schedule.task_id,
                    task_name=row.task_name,
                    project_name=row.project_name,
                    genre_color=row.genre_color,
                    allocated_hours=schedule.allocated_hours,
                    status=schedule.status,
                )
            )
            planned_hours += schedule.allocated_hours

        # Get actual hours for today
        actual_query = select(func.sum(TimeEntry.duration_minutes)).where(
            func.date(TimeEntry.start_time) == today,
            TimeEntry.duration_minutes.isnot(None),
        )
        actual_result = await session.execute(actual_query)
        actual_minutes = actual_result.scalar_one() or 0
        actual_hours = Decimal(actual_minutes) / 60

        remaining = max(Decimal("0"), planned_hours - actual_hours)

        return TodayResponse(
            date=today,
            timer=timer,
            schedules=schedules,
            summary=TodaySummary(
                planned_hours=planned_hours,
                actual_hours=actual_hours,
                remaining_hours=remaining,
            ),
        )

    # ===== Timeline =====

    async def get_timeline(
        self, session: AsyncSession, target_date: Optional[date] = None
    ) -> TimelineResponse:
        """Get timeline data for a specific date."""
        if target_date is None:
            target_date = date.today()

        # Get planned (schedules)
        planned_query = (
            select(Schedule, Task.name.label("task_name"), Genre.color.label("genre_color"))
            .join(Task, Schedule.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(func.date(Schedule.scheduled_date) == target_date)
            .where(Schedule.start_time.isnot(None))
            .where(Schedule.end_time.isnot(None))
            .order_by(Schedule.start_time)
        )
        planned_result = await session.execute(planned_query)
        planned_rows = planned_result.all()

        planned = [
            TimelineBlock(
                start=row[0].start_time.strftime("%H:%M"),
                end=row[0].end_time.strftime("%H:%M"),
                task_id=row[0].task_id,
                task_name=row.task_name,
                genre_color=row.genre_color,
            )
            for row in planned_rows
        ]

        # Get actual (time_entries)
        actual_query = (
            select(TimeEntry, Task.name.label("task_name"), Genre.color.label("genre_color"))
            .join(Task, TimeEntry.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(func.date(TimeEntry.start_time) == target_date)
            .where(TimeEntry.end_time.isnot(None))
            .order_by(TimeEntry.start_time)
        )
        actual_result = await session.execute(actual_query)
        actual_rows = actual_result.all()

        actual = [
            TimelineBlock(
                start=row[0].start_time.strftime("%H:%M"),
                end=row[0].end_time.strftime("%H:%M"),
                task_id=row[0].task_id,
                task_name=row.task_name,
                genre_color=row.genre_color,
            )
            for row in actual_rows
        ]

        return TimelineResponse(date=target_date, planned=planned, actual=actual)

    # ===== Weekly Timeline =====

    async def get_weekly_timeline(
        self,
        session: AsyncSession,
        week_start: Optional[date] = None,
        start_hour: int = 6,
        end_hour: int = 24,
    ) -> WeeklyTimelineResponse:
        """Get weekly timeline data for calendar view."""
        monday, sunday = self._get_week_bounds(week_start)
        today = date.today()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Fetch all planned schedules for the week in one query
        planned_query = (
            select(Schedule, Task.name.label("task_name"), Genre.color.label("genre_color"))
            .join(Task, Schedule.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(func.date(Schedule.scheduled_date).between(monday, sunday))
            .where(Schedule.start_time.isnot(None))
            .where(Schedule.end_time.isnot(None))
            .order_by(Schedule.start_time)
        )
        planned_result = await session.execute(planned_query)
        planned_rows = planned_result.all()

        # Group planned by date
        planned_by_date: dict[date, List[TimelineBlock]] = {
            monday + timedelta(days=i): [] for i in range(7)
        }
        for row in planned_rows:
            schedule = row[0]
            day = schedule.scheduled_date.date() if isinstance(schedule.scheduled_date, datetime) else schedule.scheduled_date
            if day in planned_by_date:
                planned_by_date[day].append(
                    TimelineBlock(
                        start=schedule.start_time.strftime("%H:%M"),
                        end=schedule.end_time.strftime("%H:%M"),
                        task_id=schedule.task_id,
                        task_name=row.task_name,
                        genre_color=row.genre_color,
                    )
                )

        # Fetch all actual time entries for the week in one query
        actual_query = (
            select(TimeEntry, Task.name.label("task_name"), Genre.color.label("genre_color"))
            .join(Task, TimeEntry.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(func.date(TimeEntry.start_time).between(monday, sunday))
            .where(TimeEntry.end_time.isnot(None))
            .order_by(TimeEntry.start_time)
        )
        actual_result = await session.execute(actual_query)
        actual_rows = actual_result.all()

        # Group actual by date
        actual_by_date: dict[date, List[TimelineBlock]] = {
            monday + timedelta(days=i): [] for i in range(7)
        }
        for row in actual_rows:
            entry = row[0]
            day = entry.start_time.date()
            if day in actual_by_date:
                actual_by_date[day].append(
                    TimelineBlock(
                        start=entry.start_time.strftime("%H:%M"),
                        end=entry.end_time.strftime("%H:%M"),
                        task_id=entry.task_id,
                        task_name=row.task_name,
                        genre_color=row.genre_color,
                    )
                )

        # Build response
        days = []
        for i in range(7):
            day = monday + timedelta(days=i)
            days.append(
                WeeklyTimelineDay(
                    date=day,
                    day_of_week=day_names[i],
                    is_today=(day == today),
                    planned=planned_by_date[day],
                    actual=actual_by_date[day],
                )
            )

        return WeeklyTimelineResponse(
            week_start=monday,
            week_end=sunday,
            start_hour=start_hour,
            end_hour=end_hour,
            days=days,
        )

    # ===== Weekly =====

    async def get_weekly(
        self, session: AsyncSession, week_start: Optional[date] = None
    ) -> WeeklyResponse:
        """Get weekly summary data."""
        monday, sunday = self._get_week_bounds(week_start)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Get daily planned hours
        planned_query = (
            select(
                func.date(Schedule.scheduled_date).label("day"),
                func.sum(Schedule.allocated_hours).label("hours"),
            )
            .where(func.date(Schedule.scheduled_date).between(monday, sunday))
            .group_by(func.date(Schedule.scheduled_date))
        )
        planned_result = await session.execute(planned_query)
        planned_by_day = {row.day: row.hours or Decimal("0") for row in planned_result.all()}

        # Get daily actual hours
        actual_query = (
            select(
                func.date(TimeEntry.start_time).label("day"),
                func.sum(TimeEntry.duration_minutes).label("minutes"),
            )
            .where(func.date(TimeEntry.start_time).between(monday, sunday))
            .where(TimeEntry.duration_minutes.isnot(None))
            .group_by(func.date(TimeEntry.start_time))
        )
        actual_result = await session.execute(actual_query)
        actual_by_day = {
            row.day: Decimal(row.minutes or 0) / 60 for row in actual_result.all()
        }

        # Build daily data
        daily = []
        total_planned = Decimal("0")
        total_actual = Decimal("0")

        for i in range(7):
            day = monday + timedelta(days=i)
            planned = planned_by_day.get(day, Decimal("0"))
            actual = actual_by_day.get(day, Decimal("0"))
            total_planned += planned
            total_actual += actual

            daily.append(
                DailyData(
                    date=day,
                    day=day_names[i],
                    planned_hours=planned,
                    actual_hours=actual,
                )
            )

        # Get hours by project
        project_query = (
            select(
                Project.name.label("name"),
                func.sum(TimeEntry.duration_minutes).label("minutes"),
            )
            .join(Task, TimeEntry.task_id == Task.id)
            .outerjoin(Project, Task.project_id == Project.id)
            .where(func.date(TimeEntry.start_time).between(monday, sunday))
            .where(TimeEntry.duration_minutes.isnot(None))
            .group_by(Project.id, Project.name)
        )
        project_result = await session.execute(project_query)
        by_project = [
            GroupedHours(
                name=row.name or "No Project",
                hours=Decimal(row.minutes or 0) / 60,
            )
            for row in project_result.all()
        ]

        # Get hours by genre
        genre_query = (
            select(
                Genre.name.label("name"),
                func.sum(TimeEntry.duration_minutes).label("minutes"),
            )
            .join(Task, TimeEntry.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(func.date(TimeEntry.start_time).between(monday, sunday))
            .where(TimeEntry.duration_minutes.isnot(None))
            .group_by(Genre.id, Genre.name)
        )
        genre_result = await session.execute(genre_query)
        by_genre = [
            GroupedHours(
                name=row.name or "No Genre",
                hours=Decimal(row.minutes or 0) / 60,
            )
            for row in genre_result.all()
        ]

        return WeeklyResponse(
            week_start=monday,
            week_end=sunday,
            daily=daily,
            totals=WeeklyTotals(
                planned_hours=total_planned,
                actual_hours=total_actual,
                by_project=by_project,
                by_genre=by_genre,
            ),
        )

    # ===== Stats =====

    async def get_stats(
        self, session: AsyncSession, period: str = "week"
    ) -> StatsResponse:
        """Get statistics for the specified period."""
        today = date.today()

        if period == "week":
            start_date, _ = self._get_week_bounds(today)
        elif period == "month":
            start_date = today.replace(day=1)
        elif period == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
        else:
            start_date, _ = self._get_week_bounds(today)

        # Estimation accuracy - completed tasks with estimates
        accuracy_query = (
            select(
                Genre.name.label("genre_name"),
                Task.estimated_hours,
                func.sum(TimeEntry.duration_minutes).label("actual_minutes"),
            )
            .join(TimeEntry, TimeEntry.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .where(
                Task.status == "done",
                Task.estimated_hours.isnot(None),
                Task.estimated_hours > 0,
                Task.updated_at >= datetime.combine(start_date, datetime.min.time()),
            )
            .group_by(Task.id, Genre.name, Task.estimated_hours)
        )
        accuracy_result = await session.execute(accuracy_query)
        accuracy_rows = accuracy_result.all()

        genre_ratios = {}
        total_ratio = Decimal("0")
        ratio_count = 0

        for row in accuracy_rows:
            if row.actual_minutes and row.estimated_hours:
                actual_hours = Decimal(row.actual_minutes) / 60
                ratio = actual_hours / row.estimated_hours
                total_ratio += ratio
                ratio_count += 1

                genre = row.genre_name or "No Genre"
                if genre not in genre_ratios:
                    genre_ratios[genre] = {"total": Decimal("0"), "count": 0}
                genre_ratios[genre]["total"] += ratio
                genre_ratios[genre]["count"] += 1

        avg_ratio = total_ratio / ratio_count if ratio_count > 0 else None
        by_genre = [
            GenreRatio(name=name, ratio=data["total"] / data["count"])
            for name, data in genre_ratios.items()
            if data["count"] > 0
        ]

        # Time distribution
        dist_query = (
            select(
                Genre.name.label("genre_name"),
                Project.name.label("project_name"),
                func.sum(TimeEntry.duration_minutes).label("minutes"),
            )
            .join(Task, TimeEntry.task_id == Task.id)
            .outerjoin(Genre, Task.genre_id == Genre.id)
            .outerjoin(Project, Task.project_id == Project.id)
            .where(
                func.date(TimeEntry.start_time) >= start_date,
                TimeEntry.duration_minutes.isnot(None),
            )
            .group_by(Genre.id, Genre.name, Project.id, Project.name)
        )
        dist_result = await session.execute(dist_query)
        dist_rows = dist_result.all()

        genre_hours = {}
        project_hours = {}
        total_hours = Decimal("0")

        for row in dist_rows:
            hours = Decimal(row.minutes or 0) / 60
            total_hours += hours

            genre = row.genre_name or "No Genre"
            project = row.project_name or "No Project"

            genre_hours[genre] = genre_hours.get(genre, Decimal("0")) + hours
            project_hours[project] = project_hours.get(project, Decimal("0")) + hours

        by_genre_dist = [
            DistributionItem(
                name=name,
                hours=hours,
                percentage=int(hours / total_hours * 100) if total_hours > 0 else 0,
            )
            for name, hours in genre_hours.items()
        ]
        by_project_dist = [
            DistributionItem(
                name=name,
                hours=hours,
                percentage=int(hours / total_hours * 100) if total_hours > 0 else 0,
            )
            for name, hours in project_hours.items()
        ]

        # Completion rate
        completion_query = select(
            func.count().filter(Task.status == "done").label("completed"),
            func.count().label("total"),
        ).where(
            Task.status.notin_(["archive"]),
            Task.created_at >= datetime.combine(start_date, datetime.min.time()),
        )
        completion_result = await session.execute(completion_query)
        completion_row = completion_result.one()
        completed = completion_row.completed or 0
        total = completion_row.total or 0
        percentage = int(completed / total * 100) if total > 0 else 0

        # Context switches (unique tasks per day)
        switch_query = (
            select(
                func.date(TimeEntry.start_time).label("day"),
                func.count(func.distinct(TimeEntry.task_id)).label("task_count"),
            )
            .where(func.date(TimeEntry.start_time) >= start_date)
            .group_by(func.date(TimeEntry.start_time))
        )
        switch_result = await session.execute(switch_query)
        switch_rows = switch_result.all()

        if switch_rows:
            switches = [max(0, row.task_count - 1) for row in switch_rows]
            avg_switches = Decimal(sum(switches)) / len(switches)

            # Simple trend: compare first half to second half
            if len(switches) >= 4:
                mid = len(switches) // 2
                first_half_avg = sum(switches[:mid]) / mid
                second_half_avg = sum(switches[mid:]) / (len(switches) - mid)
                if second_half_avg > first_half_avg * Decimal("1.1"):
                    trend = "increasing"
                elif second_half_avg < first_half_avg * Decimal("0.9"):
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            avg_switches = Decimal("0")
            trend = "stable"

        return StatsResponse(
            period=period,
            estimation_accuracy=EstimationAccuracy(
                average_ratio=avg_ratio,
                by_genre=by_genre,
            ),
            time_distribution=TimeDistribution(
                by_genre=by_genre_dist,
                by_project=by_project_dist,
            ),
            completion_rate=CompletionRate(
                tasks_completed=completed,
                tasks_total=total,
                percentage=percentage,
            ),
            context_switches=ContextSwitches(
                average_per_day=avg_switches,
                trend=trend,
            ),
        )

    # ===== Summary =====

    async def get_summary(self, session: AsyncSession) -> SummaryResponse:
        """Get overall summary for dashboard header."""
        today = date.today()
        monday, sunday = self._get_week_bounds(today)
        timer = await self._get_timer_info(session)

        # Today summary
        today_planned_query = select(
            func.coalesce(func.sum(Schedule.allocated_hours), 0).label("hours"),
            func.count().label("count"),
        ).where(func.date(Schedule.scheduled_date) == today)
        today_planned_result = await session.execute(today_planned_query)
        today_planned = today_planned_result.one()

        today_actual_query = select(
            func.coalesce(func.sum(TimeEntry.duration_minutes), 0)
        ).where(
            func.date(TimeEntry.start_time) == today,
            TimeEntry.duration_minutes.isnot(None),
        )
        today_actual_result = await session.execute(today_actual_query)
        today_actual_minutes = today_actual_result.scalar_one() or 0

        # Week summary
        week_planned_query = select(
            func.coalesce(func.sum(Schedule.allocated_hours), 0)
        ).where(func.date(Schedule.scheduled_date).between(monday, sunday))
        week_planned_result = await session.execute(week_planned_query)
        week_planned_hours = week_planned_result.scalar_one() or Decimal("0")

        week_actual_query = select(
            func.coalesce(func.sum(TimeEntry.duration_minutes), 0)
        ).where(
            func.date(TimeEntry.start_time).between(monday, sunday),
            TimeEntry.duration_minutes.isnot(None),
        )
        week_actual_result = await session.execute(week_actual_query)
        week_actual_minutes = week_actual_result.scalar_one() or 0

        # Urgent tasks
        now = datetime.now()
        urgent_query = select(
            func.count()
            .filter(and_(Task.deadline < now, Task.status.notin_(["done", "archive"])))
            .label("overdue"),
            func.count()
            .filter(
                and_(
                    Task.deadline >= now,
                    func.date(Task.deadline) <= sunday,
                    Task.status.notin_(["done", "archive"]),
                )
            )
            .label("due_this_week"),
        ).where(Task.status.notin_(["archive"]))
        urgent_result = await session.execute(urgent_query)
        urgent = urgent_result.one()

        # Blocked tasks
        blocked_query = (
            select(func.count(func.distinct(TaskDependency.task_id)))
            .join(Task, TaskDependency.depends_on_task_id == Task.id)
            .where(Task.status.notin_(["done", "archive"]))
        )
        blocked_result = await session.execute(blocked_query)
        blocked_count = blocked_result.scalar_one() or 0

        return SummaryResponse(
            today=TodayBasicSummary(
                planned_hours=today_planned.hours,
                actual_hours=Decimal(today_actual_minutes) / 60,
                tasks_scheduled=today_planned.count,
            ),
            this_week=WeekBasicSummary(
                planned_hours=week_planned_hours,
                actual_hours=Decimal(week_actual_minutes) / 60,
                target_hours=Decimal("40"),  # TODO: get from settings
            ),
            urgent=UrgentSummary(
                overdue_tasks=urgent.overdue or 0,
                due_this_week=urgent.due_this_week or 0,
                blocked_tasks=blocked_count,
            ),
            timer=timer,
        )


# Module-level instance
dashboard_service = DashboardService()
