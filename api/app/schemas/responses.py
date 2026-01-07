from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ===== Genre Response =====
class GenreResponse(BaseModel):
    """Genre response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    created_at: datetime
    updated_at: datetime


# ===== Project Response =====
class ProjectResponse(BaseModel):
    """Project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ===== Task Response =====
class TaskResponse(BaseModel):
    """Task response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: Optional[int] = None
    genre_id: Optional[int] = None
    status: str
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    priority: str
    want_level: str
    recurrence: str
    is_splittable: bool
    min_work_unit: Decimal
    parent_task_id: Optional[int] = None
    decomposition_level: int
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ===== Schedule Response =====
class ScheduleResponse(BaseModel):
    """Schedule response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    scheduled_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    allocated_hours: Decimal
    is_generated_by_ai: bool
    created_at: datetime
    updated_at: datetime


# ===== TimeEntry Response =====
class TimeEntryResponse(BaseModel):
    """TimeEntry response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ===== Setting Response =====
class SettingResponse(BaseModel):
    """Setting response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
