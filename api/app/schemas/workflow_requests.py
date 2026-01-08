from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ===== Timer Requests =====


class TimerStartRequest(BaseModel):
    """Request to start a timer."""

    task_id: Optional[int] = None
    task_name: Optional[str] = None  # Alternative: search by name


class TimerStopRequest(BaseModel):
    """Request to stop the current timer."""

    note: Optional[str] = None


# ===== Task Breakdown/Merge Requests =====


class SubtaskInput(BaseModel):
    """Input for a single subtask in breakdown."""

    name: str
    estimated_hours: Optional[Decimal] = None
    allocated_hours: Optional[Decimal] = None  # Manual override for time allocation
    genre_id: Optional[int] = None
    priority: Optional[str] = "中"
    deadline: Optional[datetime] = None
    depends_on_indices: List[int] = Field(default_factory=list)


class TaskBreakdownRequest(BaseModel):
    """Request to break down a task into subtasks."""

    task_id: int
    subtasks: List[SubtaskInput]
    reason: Optional[str] = None
    archive_original: bool = True


class TaskInput(BaseModel):
    """Input for bulk task creation."""

    name: str
    genre_id: Optional[int] = None
    estimated_hours: Optional[Decimal] = None
    priority: str = "中"
    want_level: str = "中"
    deadline: Optional[datetime] = None
    depends_on_indices: List[int] = Field(default_factory=list)


class TaskMergeRequest(BaseModel):
    """Request to merge multiple tasks into one."""

    task_ids: List[int]
    merged_task: TaskInput
    reason: Optional[str] = None


class BulkCreateTasksRequest(BaseModel):
    """Request to bulk create tasks with dependencies."""

    project_id: Optional[int] = None
    tasks: List[TaskInput]


class TaskCompleteRequest(BaseModel):
    """Request to complete a task."""

    task_id: int
    stop_timer: bool = True
    complete_schedules: bool = True


# ===== Schedule Generation Requests =====


class DailyHours(BaseModel):
    """Available hours per day of week."""

    mon: Decimal = Field(default=Decimal("6"), ge=0, le=24)
    tue: Decimal = Field(default=Decimal("6"), ge=0, le=24)
    wed: Decimal = Field(default=Decimal("4"), ge=0, le=24)
    thu: Decimal = Field(default=Decimal("6"), ge=0, le=24)
    fri: Decimal = Field(default=Decimal("6"), ge=0, le=24)
    sat: Decimal = Field(default=Decimal("3"), ge=0, le=24)
    sun: Decimal = Field(default=Decimal("0"), ge=0, le=24)


class SchedulePreferences(BaseModel):
    """User preferences for schedule generation."""

    daily_hours: DailyHours = Field(default_factory=DailyHours)
    focus_project_id: Optional[int] = None
    avoid_context_switch: bool = True
    max_hours_per_task_per_day: Decimal = Field(default=Decimal("4"), ge=1, le=12)


class FixedEvent(BaseModel):
    """Fixed event that blocks time."""

    date: datetime
    start_time: str = Field(description="HH:MM format")
    end_time: str = Field(description="HH:MM format")
    title: str


class GenerateWeeklyScheduleRequest(BaseModel):
    """Request for weekly schedule generation."""

    week_start: datetime
    preferences: SchedulePreferences = Field(default_factory=SchedulePreferences)
    fixed_events: List[FixedEvent] = Field(default_factory=list)
    clear_existing: bool = True
