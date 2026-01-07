from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


# ===== Timer Responses =====


class PreviousTimerInfo(BaseModel):
    """Info about previously stopped timer."""

    time_entry_id: int
    task_name: str
    duration_minutes: int
    stopped_at: datetime


class TimerStartResponse(BaseModel):
    """Response for timer start."""

    time_entry_id: int
    task_id: int
    task_name: str
    project_name: Optional[str] = None
    start_time: datetime
    previous_entry: Optional[PreviousTimerInfo] = None


class TimerStopResponse(BaseModel):
    """Response for timer stop."""

    time_entry_id: int
    task_id: int
    task_name: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    task_actual_hours_total: Decimal


class CurrentTimerInfo(BaseModel):
    """Current running timer info."""

    time_entry_id: int
    task_id: int
    task_name: str
    project_name: Optional[str] = None
    start_time: datetime
    elapsed_minutes: int


class LastTimerInfo(BaseModel):
    """Last stopped timer info."""

    task_name: str
    end_time: datetime
    duration_minutes: int


class TimerStatusResponse(BaseModel):
    """Response for timer status."""

    is_running: bool
    current_entry: Optional[CurrentTimerInfo] = None
    last_entry: Optional[LastTimerInfo] = None


# ===== Task Breakdown/Merge Responses =====


class TaskSummary(BaseModel):
    """Brief task summary."""

    id: int
    name: str
    status: Optional[str] = None


class TaskBreakdownResponse(BaseModel):
    """Response for task breakdown."""

    original_task: TaskSummary
    created_tasks: List[TaskSummary]
    dependencies_transferred: int
    history_id: Optional[int] = None


class TaskMergeResponse(BaseModel):
    """Response for task merge."""

    merged_task: TaskSummary
    archived_tasks: List[int]
    time_entries_transferred: int
    history_id: Optional[int] = None


class BulkCreateResponse(BaseModel):
    """Response for bulk task creation."""

    created_tasks: List[TaskSummary]
    dependencies_created: int


class TaskProgressInfo(BaseModel):
    """Task progress information."""

    task_id: int
    estimated_hours: Optional[Decimal] = None
    actual_hours: Decimal
    remaining_hours: Optional[Decimal] = None


class TaskCompleteResponse(BaseModel):
    """Response for task completion."""

    task: TaskSummary
    timer_stopped: Optional[dict] = None
    schedules_completed: int
    unblocked_tasks: List[TaskSummary]
