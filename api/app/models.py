from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


# ===== Genre =====
class Genre(SQLModel, table=True):
    __tablename__ = "genres"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    color: str = Field(max_length=7)  # #RRGGBB
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    tasks: list["Task"] = Relationship(back_populates="genre")


# ===== Project =====
class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    tasks: list["Task"] = Relationship(back_populates="project")


# ===== Task =====
class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=300)
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")
    genre_id: Optional[int] = Field(default=None, foreign_key="genres.id")
    status: str = Field(default="todo", max_length=20)
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)
    priority: str = Field(default="中", max_length=10)
    want_level: str = Field(default="中", max_length=10)
    recurrence: str = Field(default="なし", max_length=20)
    is_splittable: bool = Field(default=True)
    min_work_unit: Decimal = Field(default=Decimal("0.5"), max_digits=3, decimal_places=1)
    parent_task_id: Optional[int] = Field(default=None, foreign_key="tasks.id")
    # Auto-computed by database trigger based on parent_task_id hierarchy - do not set manually
    decomposition_level: int = Field(default=0)
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    project: Optional[Project] = Relationship(back_populates="tasks")
    genre: Optional[Genre] = Relationship(back_populates="tasks")
    time_entries: list["TimeEntry"] = Relationship(back_populates="task")
    schedules: list["Schedule"] = Relationship(back_populates="task")


# ===== Schedule =====
class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id")
    scheduled_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    allocated_hours: Decimal = Field(max_digits=4, decimal_places=2)
    is_generated_by_ai: bool = Field(default=False)
    status: str = Field(default="scheduled", max_length=20)  # scheduled, completed, skipped
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    task: Task = Relationship(back_populates="schedules")


# ===== TimeEntry =====
class TimeEntry(SQLModel, table=True):
    __tablename__ = "time_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id")
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    task: Task = Relationship(back_populates="time_entries")


# ===== TaskDependency =====
class TaskDependency(SQLModel, table=True):
    __tablename__ = "task_dependencies"

    task_id: int = Field(foreign_key="tasks.id", primary_key=True)
    depends_on_task_id: int = Field(foreign_key="tasks.id", primary_key=True)


# ===== Setting =====
class Setting(SQLModel, table=True):
    __tablename__ = "settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(max_length=100, unique=True)
    value: str  # JSONB stored as string
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ===== Create/Update Schemas =====
class TaskCreate(SQLModel):
    """Schema for creating a new task. All required fields must be provided."""
    name: str = Field(min_length=1, max_length=300)
    project_id: Optional[int] = None
    genre_id: Optional[int] = None
    status: Optional[str] = Field(default="todo", max_length=20)
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)
    priority: Optional[str] = Field(default="中", max_length=10)
    want_level: Optional[str] = Field(default="中", max_length=10)
    parent_task_id: Optional[int] = None
    note: Optional[str] = None


class TaskUpdate(SQLModel):
    """Schema for updating an existing task. All fields are optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    project_id: Optional[int] = None
    genre_id: Optional[int] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    priority: Optional[str] = None
    want_level: Optional[str] = None
    note: Optional[str] = None


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class GenreUpdate(SQLModel):
    name: Optional[str] = None
    color: Optional[str] = None


class ScheduleUpdate(SQLModel):
    scheduled_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    allocated_hours: Optional[Decimal] = None
    status: Optional[str] = None


class TimeEntryUpdate(SQLModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    note: Optional[str] = None


class SettingUpdate(SQLModel):
    value: Optional[str] = None
    description: Optional[str] = None
