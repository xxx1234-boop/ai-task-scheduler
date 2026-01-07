"""
Factory Boy factories for generating test data.

These factories provide an alternative to the fixture-based factories in conftest.py.
They're useful for creating test data without database persistence (using .build())
or for generating realistic random data with Faker.

Usage examples:
    # Create instance without saving to DB
    task = TaskFactory.build()

    # Create with specific fields
    project = ProjectFactory.build(name="特定プロジェクト", is_active=False)

    # Create with relationships
    project = ProjectFactory.build()
    task = TaskFactory.build(project_id=project.id)
"""

from datetime import datetime, timedelta
from decimal import Decimal

import factory
from faker import Faker

from app.models import Genre, Project, Schedule, Setting, Task, TimeEntry

fake = Faker(["ja_JP"])  # Japanese locale for realistic test data


class GenreFactory(factory.Factory):
    """Factory for Genre model."""

    class Meta:
        model = Genre

    name = factory.Sequence(lambda n: f"ジャンル{n}")
    color = factory.Faker("hex_color")
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class ProjectFactory(factory.Factory):
    """Factory for Project model."""

    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f"プロジェクト{n}")
    description = factory.Faker("paragraph", locale="ja_JP")
    deadline = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=fake.random_int(min=7, max=90))
    )
    is_active = True
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class TaskFactory(factory.Factory):
    """Factory for Task model."""

    class Meta:
        model = Task

    name = factory.Sequence(lambda n: f"タスク{n}")
    project_id = None  # Optional foreign key
    genre_id = None  # Optional foreign key
    status = factory.Iterator(["todo", "doing", "waiting", "done"])
    deadline = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=fake.random_int(min=1, max=30))
    )
    estimated_hours = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=1, max=40) * 0.5))
    )
    actual_hours = Decimal("0")
    priority = factory.Iterator(["高", "中", "低"])
    want_level = factory.Iterator(["高", "中", "低"])
    recurrence = factory.Iterator(["なし", "毎日", "毎週", "毎月"])
    is_splittable = True
    min_work_unit = Decimal("0.5")
    parent_task_id = None  # Optional self-referential foreign key
    # decomposition_level is auto-computed by DB trigger - not set in factory
    note = factory.Faker("text", max_nb_chars=200, locale="ja_JP")
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class ScheduleFactory(factory.Factory):
    """Factory for Schedule model."""

    class Meta:
        model = Schedule

    task_id = None  # Required foreign key (must be provided)
    scheduled_date = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=fake.random_int(min=0, max=7))
    )
    start_time = factory.LazyFunction(
        lambda: datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    )
    end_time = factory.LazyFunction(
        lambda: datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)
    )
    allocated_hours = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=1, max=8) * 0.5))
    )
    is_generated_by_ai = False
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class TimeEntryFactory(factory.Factory):
    """Factory for TimeEntry model."""

    class Meta:
        model = TimeEntry

    task_id = None  # Required foreign key (must be provided)
    start_time = factory.LazyFunction(
        lambda: datetime.now() - timedelta(hours=2)
    )
    end_time = factory.LazyFunction(lambda: datetime.now())
    duration_minutes = factory.LazyFunction(lambda: fake.random_int(min=15, max=240))
    note = factory.Faker("sentence", locale="ja_JP")
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class SettingFactory(factory.Factory):
    """Factory for Setting model."""

    class Meta:
        model = Setting

    key = factory.Sequence(lambda n: f"setting_key_{n}")
    value = factory.LazyFunction(
        lambda: '{"enabled": true, "max_value": 100}'
    )
    description = factory.Faker("sentence", locale="ja_JP")
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


# =============================================================================
# Helper functions for common test data scenarios
# =============================================================================


def create_task_with_project_and_genre() -> tuple[Task, Project, Genre]:
    """
    Create a task with associated project and genre.

    Returns:
        Tuple of (task, project, genre) instances (not persisted to DB).
    """
    project = ProjectFactory.build()
    genre = GenreFactory.build()
    task = TaskFactory.build(project_id=project.id, genre_id=genre.id)
    return task, project, genre


def create_parent_task_with_children(num_children: int = 3) -> tuple[Task, list[Task]]:
    """
    Create a parent task with multiple child tasks.

    Args:
        num_children: Number of child tasks to create.

    Returns:
        Tuple of (parent_task, list of child_tasks) (not persisted to DB).
    """
    parent = TaskFactory.build(parent_task_id=None)
    children = [
        TaskFactory.build(
            parent_task_id=parent.id,
            # decomposition_level will be auto-set by DB trigger
            name=f"{parent.name} - サブタスク{i+1}",
        )
        for i in range(num_children)
    ]
    return parent, children


def create_task_with_schedule_and_time_entries(
    num_entries: int = 2,
) -> tuple[Task, Schedule, list[TimeEntry]]:
    """
    Create a task with a schedule and multiple time entries.

    Args:
        num_entries: Number of time entries to create.

    Returns:
        Tuple of (task, schedule, list of time_entries) (not persisted to DB).
    """
    task = TaskFactory.build()
    schedule = ScheduleFactory.build(task_id=task.id)
    time_entries = [
        TimeEntryFactory.build(task_id=task.id) for _ in range(num_entries)
    ]
    return task, schedule, time_entries
