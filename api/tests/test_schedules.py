"""
Tests for Schedules CRUD API endpoints.

Schedules represent planned time allocations for tasks with foreign key to tasks.
Tests include standard CRUD and CASCADE delete behavior.

Endpoints tested:
- POST /api/v1/schedules - Create schedule
- GET /api/v1/schedules - List schedules with filtering
- GET /api/v1/schedules/{id} - Get single schedule
- PATCH /api/v1/schedules/{id} - Update schedule
- DELETE /api/v1/schedules/{id} - Delete schedule
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Schedule
from tests.utils import (
    assert_pagination_structure,
    assert_status_code,
    assert_validation_error,
    count_records,
    record_exists,
)


class TestScheduleCRUD:
    """Test standard CRUD operations for schedules."""

    async def test_create_schedule_success(
        self, client: AsyncClient, task_factory
    ):
        """Test creating a new schedule."""
        # Arrange
        task = await task_factory(name="タスク")
        schedule_data = {
            "task_id": task.id,
            "scheduled_date": datetime.now().isoformat(),
            "allocated_hours": "2.0",
        }

        # Act
        response = await client.post("/api/v1/schedules", json=schedule_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["task_id"] == task.id
        assert "id" in data
        assert "created_at" in data

    async def test_create_schedule_with_time_slots(
        self, client: AsyncClient, task_factory
    ):
        """Test creating schedule with start and end times."""
        # Arrange
        task = await task_factory(name="タスク")
        start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        end = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)

        schedule_data = {
            "task_id": task.id,
            "scheduled_date": datetime.now().isoformat(),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "allocated_hours": "2.0",
        }

        # Act
        response = await client.post("/api/v1/schedules", json=schedule_data)

        # Assert
        assert_status_code(response, 201)

    async def test_create_schedule_missing_task_id(self, client: AsyncClient):
        """Test that creating schedule without task_id fails."""
        # Arrange
        schedule_data = {
            "scheduled_date": datetime.now().isoformat(),
            "allocated_hours": "2.0",
        }

        # Act
        response = await client.post("/api/v1/schedules", json=schedule_data)

        # Assert
        assert_validation_error(response)

    async def test_list_schedules_empty(self, client: AsyncClient):
        """Test listing schedules when database is empty."""
        # Act
        response = await client.get("/api/v1/schedules")

        # Assert
        assert_pagination_structure(response, expected_total=0)

    async def test_list_schedules_with_data(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test listing multiple schedules."""
        # Arrange
        task = await task_factory(name="タスク")
        await schedule_factory(task_id=task.id)
        await schedule_factory(task_id=task.id)
        await schedule_factory(task_id=task.id)

        # Act
        response = await client.get("/api/v1/schedules")

        # Assert
        assert_pagination_structure(response, expected_total=3)

    async def test_get_schedule_by_id(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test getting a single schedule by ID."""
        # Arrange
        task = await task_factory(name="タスク")
        schedule = await schedule_factory(task_id=task.id)

        # Act
        response = await client.get(f"/api/v1/schedules/{schedule.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["id"] == schedule.id
        assert data["task_id"] == task.id

    async def test_get_schedule_not_found(self, client: AsyncClient):
        """Test getting non-existent schedule returns 404."""
        # Act
        response = await client.get("/api/v1/schedules/99999")

        # Assert
        assert_status_code(response, 404)

    async def test_update_schedule_allocated_hours(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test updating schedule allocated_hours."""
        # Arrange
        task = await task_factory(name="タスク")
        schedule = await schedule_factory(
            task_id=task.id, allocated_hours=Decimal("2.0")
        )

        # Act
        update_data = {"allocated_hours": "4.0"}
        response = await client.patch(
            f"/api/v1/schedules/{schedule.id}", json=update_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert float(data["allocated_hours"]) == 4.0

    async def test_delete_schedule(
        self, client: AsyncClient, task_factory, schedule_factory, test_session: AsyncSession
    ):
        """Test deleting a schedule."""
        # Arrange
        task = await task_factory(name="タスク")
        schedule = await schedule_factory(task_id=task.id)
        schedule_id = schedule.id

        # Act
        response = await client.delete(f"/api/v1/schedules/{schedule_id}")

        # Assert
        assert_status_code(response, 204)

        # Verify deletion
        exists = await record_exists(test_session, Schedule, schedule_id)
        assert not exists


class TestScheduleFiltering:
    """Test filtering schedules by task."""

    async def test_filter_by_task_id(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test filtering schedules by task_id."""
        # Arrange
        task1 = await task_factory(name="タスク1")
        task2 = await task_factory(name="タスク2")

        schedule1 = await schedule_factory(task_id=task1.id)
        schedule2 = await schedule_factory(task_id=task1.id)
        schedule3 = await schedule_factory(task_id=task2.id)

        # Act
        response = await client.get(f"/api/v1/schedules?task_id={task1.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        schedule_ids = [item["id"] for item in data["items"]]
        assert schedule1.id in schedule_ids
        assert schedule2.id in schedule_ids
        assert schedule3.id not in schedule_ids


class TestScheduleForeignKeys:
    """Test foreign key constraint behaviors."""

    async def test_create_schedule_with_invalid_task_id(self, client: AsyncClient):
        """Test creating schedule with non-existent task_id."""
        # Arrange
        schedule_data = {
            "task_id": 99999,  # Non-existent
            "scheduled_date": datetime.now().isoformat(),
            "allocated_hours": "2.0",
        }

        # Act
        response = await client.post("/api/v1/schedules", json=schedule_data)

        # Assert
        # Foreign key constraint violation
        assert response.status_code in [400, 422, 500]

    async def test_delete_task_with_schedules_fails(
        self, client: AsyncClient, task_factory, schedule_factory, test_session: AsyncSession
    ):
        """Test that deleting task with schedules fails due to FK constraint.

        Note: Database does not have ON DELETE CASCADE for schedules,
        so deleting a task with associated schedules will fail.
        """
        # Arrange
        task = await task_factory(name="タスク")
        task_id = task.id  # Store ID before any session issues
        schedule1 = await schedule_factory(task_id=task_id)
        schedule2 = await schedule_factory(task_id=task_id)

        # Act: Try to delete task
        response = await client.delete(f"/api/v1/tasks/{task_id}")

        # Assert: Should fail with FK violation
        # Note: After an IntegrityError, session may be in a rolled-back state,
        # so we only verify the status code here.
        assert response.status_code in [422, 409, 500]
