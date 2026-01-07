"""
Tests for Timer Workflow API endpoints.

This test file covers:
- Starting timers (by task_id or task_name)
- Auto-stopping previous timers
- Stopping timers and calculating duration
- Getting timer status

Endpoints tested:
- POST /api/v1/workflow/timer/start - Start timer for a task
- POST /api/v1/workflow/timer/stop - Stop running timer
- GET /api/v1/workflow/timer/status - Get current timer status
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.utils import assert_status_code


class TestTimerStart:
    """Test POST /api/v1/workflow/timer/start"""

    async def test_start_timer_with_task_id(self, client: AsyncClient, task_factory):
        """Test starting timer with task_id."""
        # Arrange
        task = await task_factory(name="テストタスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["task_id"] == task.id
        assert data["task_name"] == "テストタスク"
        assert "time_entry_id" in data
        assert "start_time" in data
        assert data["previous_entry"] is None

    async def test_start_timer_with_task_name(self, client: AsyncClient, task_factory):
        """Test starting timer with task_name."""
        # Arrange
        task = await task_factory(name="特定のタスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_name": "特定のタスク"},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["task_id"] == task.id
        assert data["task_name"] == "特定のタスク"

    async def test_start_timer_with_partial_task_name(
        self, client: AsyncClient, task_factory
    ):
        """Test starting timer with partial task name match."""
        # Arrange
        task = await task_factory(name="研究プロジェクトのタスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_name": "研究プロジェクト"},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["task_id"] == task.id

    async def test_start_timer_auto_stops_previous(
        self, client: AsyncClient, task_factory
    ):
        """Test that starting new timer auto-stops the previous one."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")

        # Start first timer
        await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task_a.id},
        )

        # Act - Start second timer
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task_b.id},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["task_id"] == task_b.id
        assert data["previous_entry"] is not None
        assert data["previous_entry"]["task_name"] == "タスクA"
        assert "duration_minutes" in data["previous_entry"]
        assert "stopped_at" in data["previous_entry"]

    async def test_start_timer_returns_project_name(
        self, client: AsyncClient, project_factory, task_factory
    ):
        """Test that response includes project_name when task has project."""
        # Arrange
        project = await project_factory(name="研究プロジェクト")
        task = await task_factory(name="タスク", project_id=project.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["project_name"] == "研究プロジェクト"

    async def test_start_timer_no_project(self, client: AsyncClient, task_factory):
        """Test that project_name is null when task has no project."""
        # Arrange
        task = await task_factory(name="独立タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["project_name"] is None

    async def test_start_timer_task_not_found_by_id(self, client: AsyncClient):
        """Test starting timer with non-existent task_id."""
        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": 99999},
        )

        # Assert
        assert_status_code(response, 404)

    async def test_start_timer_task_not_found_by_name(self, client: AsyncClient):
        """Test starting timer with non-existent task name."""
        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_name": "存在しないタスク名"},
        )

        # Assert
        assert_status_code(response, 404)

    async def test_start_timer_missing_both_id_and_name(self, client: AsyncClient):
        """Test starting timer without task_id or task_name."""
        # Act
        response = await client.post(
            "/api/v1/workflow/timer/start",
            json={},
        )

        # Assert
        assert_status_code(response, 422)


class TestTimerStop:
    """Test POST /api/v1/workflow/timer/stop"""

    async def test_stop_timer_success(self, client: AsyncClient, task_factory):
        """Test successfully stopping a timer."""
        # Arrange
        task = await task_factory(name="タスク")
        await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/stop",
            json={},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["task_id"] == task.id
        assert data["task_name"] == "タスク"
        assert "time_entry_id" in data
        assert "start_time" in data
        assert "end_time" in data
        assert "duration_minutes" in data

    async def test_stop_timer_with_note(self, client: AsyncClient, task_factory):
        """Test stopping timer with a note."""
        # Arrange
        task = await task_factory(name="タスク")
        await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/stop",
            json={"note": "作業完了"},
        )

        # Assert
        assert_status_code(response, 200)

    async def test_stop_timer_calculates_duration(
        self, client: AsyncClient, running_timer_factory
    ):
        """Test that duration_minutes is calculated correctly."""
        # Arrange - Use running_timer_factory which creates timer 30 mins ago
        task, entry = await running_timer_factory(name="長時間タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/stop",
            json={},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        # Should be approximately 30 minutes (allow some tolerance)
        assert data["duration_minutes"] >= 29
        assert data["duration_minutes"] <= 31

    async def test_stop_timer_returns_actual_hours_total(
        self, client: AsyncClient, task_factory, time_entry_factory
    ):
        """Test that task_actual_hours_total is calculated correctly."""
        # Arrange - Create task with existing time entry
        task = await task_factory(name="タスク")
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now() - timedelta(hours=1),
            duration_minutes=60,
        )

        # Start new timer
        await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Act
        response = await client.post(
            "/api/v1/workflow/timer/stop",
            json={},
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        # Should include 60 minutes from previous entry + current timer
        assert float(data["task_actual_hours_total"]) >= 1.0

    async def test_stop_timer_no_running_timer(self, client: AsyncClient):
        """Test stopping when no timer is running."""
        # Act
        response = await client.post(
            "/api/v1/workflow/timer/stop",
            json={},
        )

        # Assert
        assert_status_code(response, 409)
        assert "no timer" in response.json()["detail"].lower()


class TestTimerStatus:
    """Test GET /api/v1/workflow/timer/status"""

    async def test_status_when_running(
        self, client: AsyncClient, running_timer_factory
    ):
        """Test timer status when a timer is running."""
        # Arrange
        task, entry = await running_timer_factory(name="実行中タスク")

        # Act
        response = await client.get("/api/v1/workflow/timer/status")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["is_running"] is True
        assert data["current_entry"] is not None
        assert data["current_entry"]["task_id"] == task.id
        assert data["current_entry"]["task_name"] == "実行中タスク"
        assert "elapsed_minutes" in data["current_entry"]
        assert data["last_entry"] is None

    async def test_status_when_not_running(self, client: AsyncClient):
        """Test timer status when no timer is running."""
        # Act
        response = await client.get("/api/v1/workflow/timer/status")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["is_running"] is False
        assert data["current_entry"] is None

    async def test_status_shows_last_entry(
        self, client: AsyncClient, task_factory, time_entry_factory
    ):
        """Test that status shows last completed entry."""
        # Arrange
        task = await task_factory(name="完了タスク")
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now() - timedelta(minutes=30),
            duration_minutes=30,
        )

        # Act
        response = await client.get("/api/v1/workflow/timer/status")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["is_running"] is False
        assert data["last_entry"] is not None
        assert data["last_entry"]["task_name"] == "完了タスク"
        assert data["last_entry"]["duration_minutes"] == 30

    async def test_status_elapsed_minutes_calculation(
        self, client: AsyncClient, running_timer_factory
    ):
        """Test that elapsed_minutes is calculated correctly."""
        # Arrange - Timer started 30 mins ago
        task, entry = await running_timer_factory(name="タスク")

        # Act
        response = await client.get("/api/v1/workflow/timer/status")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["is_running"] is True
        # Should be approximately 30 minutes
        assert data["current_entry"]["elapsed_minutes"] >= 29
        assert data["current_entry"]["elapsed_minutes"] <= 31

    async def test_status_includes_project_name(
        self, client: AsyncClient, project_factory, task_factory
    ):
        """Test that status includes project_name when running."""
        # Arrange
        project = await project_factory(name="研究プロジェクト")
        task = await task_factory(name="タスク", project_id=project.id)

        # Start timer
        await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )

        # Act
        response = await client.get("/api/v1/workflow/timer/status")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["current_entry"]["project_name"] == "研究プロジェクト"


class TestTimerWorkflow:
    """Test complete timer workflows."""

    async def test_full_timer_workflow(
        self, client: AsyncClient, project_factory, task_factory
    ):
        """Test complete workflow: start -> check status -> stop."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        task = await task_factory(name="ワークフロータスク", project_id=project.id)

        # Start timer
        start_response = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": task.id},
        )
        assert_status_code(start_response, 200)
        start_data = start_response.json()
        time_entry_id = start_data["time_entry_id"]

        # Check status
        status_response = await client.get("/api/v1/workflow/timer/status")
        assert_status_code(status_response, 200)
        status_data = status_response.json()
        assert status_data["is_running"] is True
        assert status_data["current_entry"]["time_entry_id"] == time_entry_id

        # Stop timer
        stop_response = await client.post(
            "/api/v1/workflow/timer/stop",
            json={"note": "完了"},
        )
        assert_status_code(stop_response, 200)
        stop_data = stop_response.json()
        assert stop_data["time_entry_id"] == time_entry_id

        # Verify timer is stopped
        final_status_response = await client.get("/api/v1/workflow/timer/status")
        final_status_data = final_status_response.json()
        assert final_status_data["is_running"] is False

    async def test_multiple_timer_switches(
        self, client: AsyncClient, task_factory
    ):
        """Test switching between multiple tasks."""
        # Arrange
        tasks = [await task_factory(name=f"タスク{i}") for i in range(3)]

        # Start timer for first task
        response1 = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": tasks[0].id},
        )
        assert_status_code(response1, 200)
        assert response1.json()["previous_entry"] is None

        # Switch to second task
        response2 = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": tasks[1].id},
        )
        assert_status_code(response2, 200)
        assert response2.json()["previous_entry"]["task_name"] == "タスク0"

        # Switch to third task
        response3 = await client.post(
            "/api/v1/workflow/timer/start",
            json={"task_id": tasks[2].id},
        )
        assert_status_code(response3, 200)
        assert response3.json()["previous_entry"]["task_name"] == "タスク1"

        # Verify current status
        status_response = await client.get("/api/v1/workflow/timer/status")
        status_data = status_response.json()
        assert status_data["current_entry"]["task_name"] == "タスク2"
