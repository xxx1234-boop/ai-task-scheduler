"""
Tests for Dashboard API endpoints.

This test file covers:
- Dashboard summary (header data)
- Today's schedule view
- Kanban board data
- Timeline view
- Weekly summary
- Statistics

Endpoints tested:
- GET /api/v1/dashboard/summary - Overall summary
- GET /api/v1/dashboard/today - Today's schedule
- GET /api/v1/dashboard/kanban - Kanban board
- GET /api/v1/dashboard/timeline - Timeline view
- GET /api/v1/dashboard/weekly - Weekly summary
- GET /api/v1/dashboard/stats - Statistics
"""

from datetime import datetime, date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.utils import assert_status_code


class TestDashboardSummary:
    """Test GET /api/v1/dashboard/summary"""

    async def test_summary_empty_data(self, client: AsyncClient):
        """Test summary with no data."""
        # Act
        response = await client.get("/api/v1/dashboard/summary")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert "today" in data
        assert "this_week" in data
        assert "urgent" in data
        assert "timer" in data
        assert data["timer"]["is_running"] is False

    async def test_summary_with_today_schedule(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test summary with today's schedules."""
        # Arrange
        task = await task_factory(name="今日のタスク")
        await schedule_factory(
            task_id=task.id,
            scheduled_date=date.today(),
            allocated_hours=Decimal("2.0"),
        )

        # Act
        response = await client.get("/api/v1/dashboard/summary")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert float(data["today"]["planned_hours"]) == 2.0
        assert data["today"]["tasks_scheduled"] >= 1

    async def test_summary_with_today_time_entries(
        self, client: AsyncClient, task_factory, time_entry_factory
    ):
        """Test summary with today's time entries."""
        # Arrange
        task = await task_factory(name="作業タスク")
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_minutes=60,
        )

        # Act
        response = await client.get("/api/v1/dashboard/summary")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert float(data["today"]["actual_hours"]) >= 1.0

    async def test_summary_urgent_overdue_tasks(
        self, client: AsyncClient, task_factory
    ):
        """Test summary counts overdue tasks."""
        # Arrange
        await task_factory(
            name="期限切れタスク",
            deadline=datetime.now() - timedelta(days=1),
            status="todo",
        )

        # Act
        response = await client.get("/api/v1/dashboard/summary")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["urgent"]["overdue_tasks"] >= 1

    async def test_summary_urgent_due_this_week(
        self, client: AsyncClient, task_factory
    ):
        """Test summary counts tasks due this week."""
        # Arrange
        await task_factory(
            name="今週期限タスク",
            deadline=datetime.now() + timedelta(days=2),
            status="todo",
        )

        # Act
        response = await client.get("/api/v1/dashboard/summary")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["urgent"]["due_this_week"] >= 1

    async def test_summary_timer_running(
        self, client: AsyncClient, running_timer_factory
    ):
        """Test summary shows running timer."""
        # Arrange
        task, entry = await running_timer_factory(name="実行中タスク")

        # Act
        response = await client.get("/api/v1/dashboard/summary")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["timer"]["is_running"] is True
        assert data["timer"]["task_name"] == "実行中タスク"
        assert data["timer"]["elapsed_minutes"] >= 0


class TestDashboardToday:
    """Test GET /api/v1/dashboard/today"""

    async def test_today_empty(self, client: AsyncClient):
        """Test today with no data."""
        # Act
        response = await client.get("/api/v1/dashboard/today")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["date"] == str(date.today())
        assert data["schedules"] == []
        assert data["timer"]["is_running"] is False

    async def test_today_with_schedules(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test today with schedules."""
        # Arrange
        task = await task_factory(name="予定タスク")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        await schedule_factory(
            task_id=task.id,
            scheduled_date=today,
            allocated_hours=Decimal("1.5"),
            start_time=today.replace(hour=9, minute=0),
            end_time=today.replace(hour=10, minute=30),
        )

        # Act
        response = await client.get("/api/v1/dashboard/today")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["schedules"]) >= 1
        schedule = data["schedules"][0]
        assert schedule["task_name"] == "予定タスク"
        assert float(schedule["allocated_hours"]) == 1.5

    async def test_today_schedule_includes_project_genre(
        self, client: AsyncClient, project_factory, genre_factory, task_factory, schedule_factory
    ):
        """Test today schedule includes project and genre info."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        genre = await genre_factory(name="リサーチ", color="#FF5733")
        task = await task_factory(name="タスク", project_id=project.id, genre_id=genre.id)
        await schedule_factory(
            task_id=task.id,
            scheduled_date=date.today(),
            allocated_hours=Decimal("1.0"),
        )

        # Act
        response = await client.get("/api/v1/dashboard/today")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        schedule = data["schedules"][0]
        assert schedule["project_name"] == "プロジェクト"
        assert schedule["genre_color"] == "#FF5733"

    async def test_today_summary_calculations(
        self, client: AsyncClient, task_factory, schedule_factory, time_entry_factory
    ):
        """Test today summary calculations."""
        # Arrange
        task = await task_factory(name="タスク")
        await schedule_factory(
            task_id=task.id,
            scheduled_date=date.today(),
            allocated_hours=Decimal("3.0"),
        )
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_minutes=60,
        )

        # Act
        response = await client.get("/api/v1/dashboard/today")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert float(data["summary"]["planned_hours"]) == 3.0
        assert float(data["summary"]["actual_hours"]) >= 1.0
        # remaining = planned - actual
        assert float(data["summary"]["remaining_hours"]) <= 2.0

    async def test_today_timer_status(
        self, client: AsyncClient, running_timer_factory
    ):
        """Test today shows timer status."""
        # Arrange
        await running_timer_factory(name="実行中タスク")

        # Act
        response = await client.get("/api/v1/dashboard/today")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["timer"]["is_running"] is True


class TestDashboardKanban:
    """Test GET /api/v1/dashboard/kanban"""

    async def test_kanban_structure(self, client: AsyncClient):
        """Test kanban response structure."""
        # Act
        response = await client.get("/api/v1/dashboard/kanban")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert "columns" in data
        assert "counts" in data
        # Verify all status columns exist
        assert "todo" in data["columns"]
        assert "doing" in data["columns"]
        assert "waiting" in data["columns"]
        assert "done" in data["columns"]
        # Verify counts structure
        assert "todo" in data["counts"]
        assert "doing" in data["counts"]
        assert "waiting" in data["counts"]
        assert "done" in data["counts"]

    async def test_kanban_groups_by_status(self, client: AsyncClient, task_factory):
        """Test kanban groups tasks by status."""
        # Arrange
        await task_factory(name="TODOタスク", status="todo")
        await task_factory(name="DOINGタスク", status="doing")
        await task_factory(name="WAITINGタスク", status="waiting")
        await task_factory(name="DONEタスク", status="done")

        # Act
        response = await client.get("/api/v1/dashboard/kanban")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["columns"]["todo"]) >= 1
        assert len(data["columns"]["doing"]) >= 1
        assert len(data["columns"]["waiting"]) >= 1
        assert len(data["columns"]["done"]) >= 1

    async def test_kanban_excludes_archive(self, client: AsyncClient, task_factory):
        """Test kanban excludes archived tasks."""
        # Arrange
        await task_factory(name="アーカイブタスク", status="archive")
        await task_factory(name="通常タスク", status="todo")

        # Act
        response = await client.get("/api/v1/dashboard/kanban")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        all_tasks = (
            data["columns"]["todo"]
            + data["columns"]["doing"]
            + data["columns"]["waiting"]
            + data["columns"]["done"]
        )
        task_names = [t["name"] for t in all_tasks]
        assert "アーカイブタスク" not in task_names
        assert "通常タスク" in task_names

    async def test_kanban_includes_blocked_by(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test kanban includes blocked_by information."""
        # Arrange
        blocking_task = await task_factory(name="ブロック元タスク", status="todo")
        blocked_task = await task_factory(name="ブロックタスク", status="todo")
        await task_dependency_factory(
            task_id=blocked_task.id, depends_on_task_id=blocking_task.id
        )

        # Act
        response = await client.get("/api/v1/dashboard/kanban")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        # Find blocked task
        for task in data["columns"]["todo"]:
            if task["name"] == "ブロックタスク":
                assert "ブロック元タスク" in task["blocked_by"]
                break

    async def test_kanban_filter_by_project(
        self, client: AsyncClient, project_factory, task_factory
    ):
        """Test kanban filtering by project_id."""
        # Arrange
        project = await project_factory(name="対象プロジェクト")
        other_project = await project_factory(name="他のプロジェクト")
        await task_factory(name="対象タスク", project_id=project.id, status="todo")
        await task_factory(name="他タスク", project_id=other_project.id, status="todo")

        # Act
        response = await client.get(f"/api/v1/dashboard/kanban?project_id={project.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        all_tasks = data["columns"]["todo"]
        task_names = [t["name"] for t in all_tasks]
        assert "対象タスク" in task_names
        assert "他タスク" not in task_names

    async def test_kanban_counts_correct(self, client: AsyncClient, task_factory):
        """Test kanban counts are correct."""
        # Arrange
        await task_factory(name="TODO1", status="todo")
        await task_factory(name="TODO2", status="todo")
        await task_factory(name="DOING1", status="doing")

        # Act
        response = await client.get("/api/v1/dashboard/kanban")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["counts"]["todo"] >= 2
        assert data["counts"]["doing"] >= 1

    async def test_kanban_task_includes_details(
        self, client: AsyncClient, project_factory, genre_factory, task_factory
    ):
        """Test kanban task includes all required details."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        genre = await genre_factory(name="リサーチ", color="#FF5733")
        task = await task_factory(
            name="詳細タスク",
            project_id=project.id,
            genre_id=genre.id,
            priority="高",
            estimated_hours=Decimal("3.0"),
            status="todo",
        )

        # Act
        response = await client.get("/api/v1/dashboard/kanban")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        kanban_task = next(
            (t for t in data["columns"]["todo"] if t["name"] == "詳細タスク"), None
        )
        assert kanban_task is not None
        assert kanban_task["project_name"] == "プロジェクト"
        assert kanban_task["genre_name"] == "リサーチ"
        assert kanban_task["genre_color"] == "#FF5733"
        assert kanban_task["priority"] == "高"
        assert float(kanban_task["estimated_hours"]) == 3.0


class TestDashboardTimeline:
    """Test GET /api/v1/dashboard/timeline"""

    async def test_timeline_structure(self, client: AsyncClient):
        """Test timeline response structure."""
        # Act
        response = await client.get("/api/v1/dashboard/timeline")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["date"] == str(date.today())
        assert "planned" in data
        assert "actual" in data
        assert isinstance(data["planned"], list)
        assert isinstance(data["actual"], list)

    async def test_timeline_planned_blocks(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test timeline shows planned blocks from schedules."""
        # Arrange
        task = await task_factory(name="予定タスク")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        await schedule_factory(
            task_id=task.id,
            scheduled_date=today,
            start_time=today.replace(hour=9, minute=0),
            end_time=today.replace(hour=11, minute=0),
            allocated_hours=Decimal("2.0"),
        )

        # Act
        response = await client.get("/api/v1/dashboard/timeline")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["planned"]) >= 1
        block = data["planned"][0]
        assert block["task_name"] == "予定タスク"
        assert block["start"] == "09:00"
        assert block["end"] == "11:00"

    async def test_timeline_actual_blocks(
        self, client: AsyncClient, task_factory, time_entry_factory
    ):
        """Test timeline shows actual blocks from time entries."""
        # Arrange
        task = await task_factory(name="作業タスク")
        now = datetime.now()
        start = now.replace(hour=10, minute=0, second=0, microsecond=0)
        end = now.replace(hour=12, minute=0, second=0, microsecond=0)
        await time_entry_factory(
            task_id=task.id,
            start_time=start,
            end_time=end,
            duration_minutes=120,
        )

        # Act
        response = await client.get("/api/v1/dashboard/timeline")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["actual"]) >= 1
        block = data["actual"][0]
        assert block["task_name"] == "作業タスク"

    async def test_timeline_specific_date(
        self, client: AsyncClient, task_factory, schedule_factory
    ):
        """Test timeline for a specific date."""
        # Arrange
        task = await task_factory(name="過去タスク")
        target_date = date.today() - timedelta(days=1)
        target_dt = datetime.combine(target_date, datetime.min.time())
        await schedule_factory(
            task_id=task.id,
            scheduled_date=target_dt,
            start_time=target_dt.replace(hour=10, minute=0),
            end_time=target_dt.replace(hour=12, minute=0),
            allocated_hours=Decimal("2.0"),
        )

        # Act
        response = await client.get(f"/api/v1/dashboard/timeline?target_date={target_date}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["date"] == str(target_date)
        assert len(data["planned"]) >= 1


class TestDashboardWeekly:
    """Test GET /api/v1/dashboard/weekly"""

    async def test_weekly_empty(self, client: AsyncClient):
        """Test weekly with no data."""
        # Act
        response = await client.get("/api/v1/dashboard/weekly")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert "week_start" in data
        assert "week_end" in data
        assert "daily" in data
        assert "totals" in data
        assert len(data["daily"]) == 7  # Always 7 days

    async def test_weekly_daily_data(
        self, client: AsyncClient, task_factory, schedule_factory, time_entry_factory
    ):
        """Test weekly shows daily data."""
        # Arrange
        task = await task_factory(name="タスク")
        today = date.today()
        await schedule_factory(
            task_id=task.id,
            scheduled_date=today,
            allocated_hours=Decimal("4.0"),
        )
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now(),
            duration_minutes=120,
        )

        # Act
        response = await client.get("/api/v1/dashboard/weekly")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        # Find today in daily
        today_data = next((d for d in data["daily"] if d["date"] == str(today)), None)
        if today_data:
            assert float(today_data["planned_hours"]) >= 4.0
            assert float(today_data["actual_hours"]) >= 2.0

    async def test_weekly_by_project(
        self, client: AsyncClient, project_factory, task_factory, time_entry_factory
    ):
        """Test weekly totals by project."""
        # Arrange
        project = await project_factory(name="プロジェクトA")
        task = await task_factory(name="タスク", project_id=project.id)
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_minutes=60,
        )

        # Act
        response = await client.get("/api/v1/dashboard/weekly")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        by_project = data["totals"]["by_project"]
        project_entry = next((p for p in by_project if p["name"] == "プロジェクトA"), None)
        if project_entry:
            assert float(project_entry["hours"]) >= 1.0

    async def test_weekly_by_genre(
        self, client: AsyncClient, genre_factory, task_factory, time_entry_factory
    ):
        """Test weekly totals by genre."""
        # Arrange
        genre = await genre_factory(name="リサーチ")
        task = await task_factory(name="タスク", genre_id=genre.id)
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_minutes=60,
        )

        # Act
        response = await client.get("/api/v1/dashboard/weekly")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        by_genre = data["totals"]["by_genre"]
        genre_entry = next((g for g in by_genre if g["name"] == "リサーチ"), None)
        if genre_entry:
            assert float(genre_entry["hours"]) >= 1.0

    async def test_weekly_custom_start_date(self, client: AsyncClient):
        """Test weekly with custom week_start."""
        # Arrange
        last_monday = date.today() - timedelta(days=date.today().weekday() + 7)

        # Act
        response = await client.get(f"/api/v1/dashboard/weekly?week_start={last_monday}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["week_start"] == str(last_monday)


class TestDashboardStats:
    """Test GET /api/v1/dashboard/stats"""

    async def test_stats_empty(self, client: AsyncClient):
        """Test stats with no data."""
        # Act
        response = await client.get("/api/v1/dashboard/stats")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["period"] == "week"
        assert "estimation_accuracy" in data
        assert "time_distribution" in data
        assert "completion_rate" in data
        assert "context_switches" in data

    async def test_stats_week_period(self, client: AsyncClient):
        """Test stats with week period."""
        # Act
        response = await client.get("/api/v1/dashboard/stats?period=week")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["period"] == "week"

    async def test_stats_month_period(self, client: AsyncClient):
        """Test stats with month period."""
        # Act
        response = await client.get("/api/v1/dashboard/stats?period=month")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["period"] == "month"

    async def test_stats_quarter_period(self, client: AsyncClient):
        """Test stats with quarter period."""
        # Act
        response = await client.get("/api/v1/dashboard/stats?period=quarter")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["period"] == "quarter"

    async def test_stats_completion_rate(self, client: AsyncClient, task_factory):
        """Test stats completion rate calculation."""
        # Arrange
        await task_factory(name="完了タスク", status="done")
        await task_factory(name="未完了タスク", status="todo")

        # Act
        response = await client.get("/api/v1/dashboard/stats?period=week")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        cr = data["completion_rate"]
        assert cr["tasks_total"] >= 2
        assert cr["tasks_completed"] >= 1
        assert 0 <= cr["percentage"] <= 100

    async def test_stats_time_distribution(
        self, client: AsyncClient, genre_factory, task_factory, time_entry_factory
    ):
        """Test stats time distribution."""
        # Arrange
        genre = await genre_factory(name="リサーチ")
        task = await task_factory(name="タスク", genre_id=genre.id)
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now(),
            duration_minutes=120,
        )

        # Act
        response = await client.get("/api/v1/dashboard/stats?period=week")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        dist = data["time_distribution"]
        assert "by_genre" in dist
        assert "by_project" in dist

    async def test_stats_context_switches(
        self, client: AsyncClient, task_factory, time_entry_factory
    ):
        """Test stats context switches calculation."""
        # Arrange - Create multiple time entries to simulate context switches
        task1 = await task_factory(name="タスク1")
        task2 = await task_factory(name="タスク2")

        now = datetime.now()
        # Switch between tasks
        await time_entry_factory(
            task_id=task1.id,
            start_time=now - timedelta(hours=4),
            end_time=now - timedelta(hours=3),
            duration_minutes=60,
        )
        await time_entry_factory(
            task_id=task2.id,
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=2),
            duration_minutes=60,
        )
        await time_entry_factory(
            task_id=task1.id,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            duration_minutes=60,
        )

        # Act
        response = await client.get("/api/v1/dashboard/stats?period=week")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        cs = data["context_switches"]
        assert "average_per_day" in cs
        assert "trend" in cs
        assert cs["trend"] in ["increasing", "decreasing", "stable"]
