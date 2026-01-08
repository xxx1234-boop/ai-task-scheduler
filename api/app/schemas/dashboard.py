from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


# ===== Common =====


class TimerInfo(BaseModel):
    """Timer status info for dashboard."""

    is_running: bool
    task_name: Optional[str] = None
    elapsed_minutes: Optional[int] = None


# ===== Kanban =====


class KanbanTaskItem(BaseModel):
    """Task item in kanban board."""

    id: int
    name: str
    description: str
    project_name: Optional[str] = None
    genre_name: Optional[str] = None
    genre_color: Optional[str] = None
    priority: str
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Decimal = Decimal("0")
    blocked_by: List[str] = []
    is_timer_running: bool = False


class KanbanColumns(BaseModel):
    """Kanban columns by status."""

    todo: List[KanbanTaskItem] = []
    doing: List[KanbanTaskItem] = []
    waiting: List[KanbanTaskItem] = []
    done: List[KanbanTaskItem] = []


class KanbanCounts(BaseModel):
    """Task counts per column."""

    todo: int = 0
    doing: int = 0
    waiting: int = 0
    done: int = 0


class KanbanResponse(BaseModel):
    """Response for /dashboard/kanban."""

    columns: KanbanColumns
    counts: KanbanCounts


# ===== Today =====


class TodayScheduleItem(BaseModel):
    """Schedule item for today."""

    id: int
    start_time: Optional[str] = None  # "HH:MM"
    end_time: Optional[str] = None  # "HH:MM"
    task_id: int
    task_name: str
    project_name: Optional[str] = None
    genre_color: Optional[str] = None
    allocated_hours: Decimal
    status: str


class TodaySummary(BaseModel):
    """Summary for today."""

    planned_hours: Decimal = Decimal("0")
    actual_hours: Decimal = Decimal("0")
    remaining_hours: Decimal = Decimal("0")


class TodayResponse(BaseModel):
    """Response for /dashboard/today."""

    date: date
    timer: TimerInfo
    schedules: List[TodayScheduleItem] = []
    summary: TodaySummary


# ===== Timeline =====


class TimelineBlock(BaseModel):
    """Time block in timeline."""

    start: str  # "HH:MM"
    end: str  # "HH:MM"
    task_id: int
    task_name: str
    genre_color: Optional[str] = None


class TimelineResponse(BaseModel):
    """Response for /dashboard/timeline."""

    date: date
    planned: List[TimelineBlock] = []
    actual: List[TimelineBlock] = []


# ===== Weekly Timeline =====


class WeeklyTimelineDay(BaseModel):
    """Single day's timeline data in weekly view."""

    date: date
    day_of_week: str  # "Mon", "Tue", etc.
    is_today: bool
    planned: List[TimelineBlock] = []
    actual: List[TimelineBlock] = []


class WeeklyTimelineResponse(BaseModel):
    """Response for /dashboard/weekly-timeline."""

    week_start: date
    week_end: date
    start_hour: int  # e.g., 6 (06:00)
    end_hour: int  # e.g., 24 (00:00 next day)
    days: List[WeeklyTimelineDay]


# ===== Weekly =====


class GroupedHours(BaseModel):
    """Hours grouped by category."""

    name: str
    hours: Decimal = Decimal("0")


class DailyData(BaseModel):
    """Daily summary data."""

    date: date
    day: str  # "Mon", "Tue", etc.
    planned_hours: Decimal = Decimal("0")
    actual_hours: Decimal = Decimal("0")


class WeeklyTotals(BaseModel):
    """Weekly totals."""

    planned_hours: Decimal = Decimal("0")
    actual_hours: Decimal = Decimal("0")
    by_project: List[GroupedHours] = []
    by_genre: List[GroupedHours] = []


class WeeklyResponse(BaseModel):
    """Response for /dashboard/weekly."""

    week_start: date
    week_end: date
    daily: List[DailyData] = []
    totals: WeeklyTotals


# ===== Stats =====


class GenreRatio(BaseModel):
    """Estimation accuracy by genre."""

    name: str
    ratio: Decimal


class EstimationAccuracy(BaseModel):
    """Estimation accuracy stats."""

    average_ratio: Optional[Decimal] = None
    by_genre: List[GenreRatio] = []


class DistributionItem(BaseModel):
    """Time distribution item."""

    name: str
    hours: Decimal = Decimal("0")
    percentage: int = 0


class TimeDistribution(BaseModel):
    """Time distribution stats."""

    by_genre: List[DistributionItem] = []
    by_project: List[DistributionItem] = []


class CompletionRate(BaseModel):
    """Task completion rate."""

    tasks_completed: int = 0
    tasks_total: int = 0
    percentage: int = 0


class ContextSwitches(BaseModel):
    """Context switch stats."""

    average_per_day: Decimal = Decimal("0")
    trend: str = "stable"  # "increasing", "decreasing", "stable"


class StatsResponse(BaseModel):
    """Response for /dashboard/stats."""

    period: str
    estimation_accuracy: EstimationAccuracy
    time_distribution: TimeDistribution
    completion_rate: CompletionRate
    context_switches: ContextSwitches


# ===== Summary =====


class TodayBasicSummary(BaseModel):
    """Basic today summary for header."""

    planned_hours: Decimal = Decimal("0")
    actual_hours: Decimal = Decimal("0")
    tasks_scheduled: int = 0


class WeekBasicSummary(BaseModel):
    """Basic week summary for header."""

    planned_hours: Decimal = Decimal("0")
    actual_hours: Decimal = Decimal("0")
    target_hours: Decimal = Decimal("40")


class UrgentSummary(BaseModel):
    """Urgent tasks summary."""

    overdue_tasks: int = 0
    due_this_week: int = 0
    blocked_tasks: int = 0


class SummaryResponse(BaseModel):
    """Response for /dashboard/summary."""

    today: TodayBasicSummary
    this_week: WeekBasicSummary
    urgent: UrgentSummary
    timer: TimerInfo
