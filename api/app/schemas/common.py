from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar, List, Optional

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: List[T]
    total: int
    skip: int = 0
    limit: int = 50


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict

    @classmethod
    def create(cls, code: str, message: str, details: dict = None):
        """Create error response with standard format."""
        return cls(
            error={"code": code, "message": message, "details": details or {}}
        )


# ===== Create Request Schemas =====


class ProjectCreate(BaseModel):
    """Request schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str  # 必須
    deadline: Optional[datetime] = None
    is_active: bool = True


class GenreCreate(BaseModel):
    """Request schema for creating a genre."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., min_length=1, max_length=7)


class TaskCreate(BaseModel):
    """Request schema for creating a task."""

    name: str = Field(..., min_length=1, max_length=300)
    project_id: Optional[int] = None
    genre_id: Optional[int] = None
    status: str = "todo"
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    priority: str = "中"
    want_level: str = "中"
    recurrence: str = "なし"
    is_splittable: bool = True
    min_work_unit: Decimal = Decimal("0.5")
    parent_task_id: Optional[int] = None
    note: Optional[str] = None


class ScheduleCreate(BaseModel):
    """Request schema for creating a schedule."""

    task_id: int
    scheduled_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    allocated_hours: Decimal = Decimal("1.0")
    is_generated_by_ai: bool = False


class TimeEntryCreate(BaseModel):
    """Request schema for creating a time entry."""

    task_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    note: Optional[str] = None


class SettingCreate(BaseModel):
    """Request schema for creating/updating a setting."""

    key: Optional[str] = Field(None, min_length=1, max_length=100)  # Optional - can use URL path key
    value: str
    description: Optional[str] = None
