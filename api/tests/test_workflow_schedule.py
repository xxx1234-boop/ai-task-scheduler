"""Tests for schedule generation workflow API."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models import Task, Schedule


class TestGenerateWeeklySchedule:
    """Tests for POST /api/v1/workflow/schedule/generate-weekly"""

    @pytest.fixture
    async def sample_tasks(self, task_factory, project_factory, genre_factory):
        """Create sample tasks for scheduling."""
        project = await project_factory(name="研究プロジェクト")
        genre = await genre_factory(name="リサーチ", color="#4A90D9")

        task1 = await task_factory(
            name="論文読み",
            project_id=project.id,
            genre_id=genre.id,
            status="todo",
            priority="高",
            estimated_hours=Decimal("6.0"),
        )
        task2 = await task_factory(
            name="データ分析",
            project_id=project.id,
            genre_id=genre.id,
            status="doing",
            priority="中",
            estimated_hours=Decimal("4.0"),
        )
        task3 = await task_factory(
            name="レポート作成",
            project_id=project.id,
            genre_id=genre.id,
            status="waiting",
            priority="低",
            estimated_hours=Decimal("3.0"),
            deadline=datetime.now() + timedelta(days=5),
        )

        return [task1, task2, task3]

    @pytest.mark.asyncio
    async def test_generate_schedule_no_tasks(self, client: AsyncClient):
        """Test schedule generation with no schedulable tasks."""
        from unittest.mock import patch, AsyncMock

        week_start = datetime.now() + timedelta(days=7)

        # Mock the service to return no schedulable tasks
        with patch(
            "app.services.schedule_service.ScheduleService._gather_schedulable_tasks",
            new_callable=AsyncMock,
        ) as mock_gather:
            mock_gather.return_value = []

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={"week_start": week_start.isoformat()},
            )

            # With no tasks, should return empty schedules (but still 201)
            assert response.status_code == 201
            data = response.json()
            assert data["schedules"] == []
            assert "スケジュール可能なタスクがありません" in data["warnings"]

    @pytest.mark.asyncio
    async def test_generate_schedule_no_api_key(
        self, client: AsyncClient, sample_tasks
    ):
        """Test schedule generation fails gracefully without API key."""
        from app.clients.claude_client import ClaudeAPIException

        week_start = datetime.now() + timedelta(days=7)

        # Mock ClaudeClient to raise exception for missing API key
        with patch(
            "app.services.schedule_service.ClaudeClient"
        ) as MockClaudeClient:
            mock_client = AsyncMock()
            mock_client.generate_schedule.side_effect = ClaudeAPIException(
                "ANTHROPIC_API_KEY is not configured", status_code=503
            )
            MockClaudeClient.return_value = mock_client

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={"week_start": week_start.isoformat()},
            )

            assert response.status_code == 503
            assert "api_key" in response.json()["detail"].lower() or "api key" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_schedule_success(
        self, client: AsyncClient, sample_tasks, test_session
    ):
        """Test successful schedule generation with mocked Claude API."""
        week_start = datetime.now() + timedelta(days=7)
        week_start_str = week_start.strftime("%Y-%m-%d")

        # Mock Claude API response
        mock_response = f"""[
            {{"task_id": {sample_tasks[0].id}, "date": "{week_start_str}", "start_time": "09:00", "end_time": "12:00", "allocated_hours": 3.0, "reasoning": "高優先度"}},
            {{"task_id": {sample_tasks[0].id}, "date": "{(week_start + timedelta(days=1)).strftime("%Y-%m-%d")}", "start_time": "09:00", "end_time": "12:00", "allocated_hours": 3.0, "reasoning": "高優先度"}},
            {{"task_id": {sample_tasks[1].id}, "date": "{week_start_str}", "start_time": "13:00", "end_time": "17:00", "allocated_hours": 4.0, "reasoning": "継続中のタスク"}}
        ]"""

        with patch(
            "app.services.schedule_service.ClaudeClient"
        ) as MockClaudeClient:
            mock_client = AsyncMock()
            mock_client.generate_schedule.return_value = mock_response
            MockClaudeClient.return_value = mock_client

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={
                    "week_start": week_start.isoformat(),
                    "preferences": {
                        "daily_hours": {
                            "mon": 6,
                            "tue": 6,
                            "wed": 4,
                            "thu": 6,
                            "fri": 6,
                            "sat": 3,
                            "sun": 0,
                        }
                    },
                },
            )

            assert response.status_code == 201
            data = response.json()

            # Check response structure
            assert "schedules" in data
            assert "summary" in data
            assert "warnings" in data
            assert len(data["schedules"]) == 3

            # Check summary (Decimal is serialized as string)
            assert float(data["summary"]["total_planned_hours"]) == 10.0

            # Verify Claude client was called
            mock_client.generate_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_schedule_with_dependencies(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test schedule generation respects task dependencies."""
        task1 = await task_factory(
            name="準備タスク",
            status="todo",
            priority="高",
            estimated_hours=Decimal("2.0"),
        )
        task2 = await task_factory(
            name="依存タスク",
            status="todo",
            priority="高",
            estimated_hours=Decimal("2.0"),
        )

        # task2 depends on task1
        await task_dependency_factory(
            task_id=task2.id, depends_on_task_id=task1.id
        )

        week_start = datetime.now() + timedelta(days=7)
        week_start_str = week_start.strftime("%Y-%m-%d")

        # Mock response with wrong dependency order (to trigger warning)
        mock_response = f"""[
            {{"task_id": {task2.id}, "date": "{week_start_str}", "start_time": "09:00", "end_time": "11:00", "allocated_hours": 2.0}},
            {{"task_id": {task1.id}, "date": "{week_start_str}", "start_time": "13:00", "end_time": "15:00", "allocated_hours": 2.0}}
        ]"""

        with patch(
            "app.services.schedule_service.ClaudeClient"
        ) as MockClaudeClient:
            mock_client = AsyncMock()
            mock_client.generate_schedule.return_value = mock_response
            MockClaudeClient.return_value = mock_client

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={"week_start": week_start.isoformat()},
            )

            assert response.status_code == 201
            data = response.json()

            # Should have dependency violation warning
            assert any("依存関係" in w for w in data["warnings"])

    @pytest.mark.asyncio
    async def test_generate_schedule_clears_existing(
        self, client: AsyncClient, sample_tasks, schedule_factory, test_session
    ):
        """Test that existing AI-generated schedules are cleared."""
        week_start = datetime.now() + timedelta(days=7)

        # Create existing AI-generated schedule
        existing_schedule = await schedule_factory(
            task_id=sample_tasks[0].id,
            scheduled_date=week_start,
            allocated_hours=Decimal("2.0"),
            is_generated_by_ai=True,
            status="scheduled",
        )

        week_start_str = week_start.strftime("%Y-%m-%d")
        mock_response = f"""[
            {{"task_id": {sample_tasks[0].id}, "date": "{week_start_str}", "start_time": "09:00", "end_time": "12:00", "allocated_hours": 3.0}}
        ]"""

        with patch(
            "app.services.schedule_service.ClaudeClient"
        ) as MockClaudeClient:
            mock_client = AsyncMock()
            mock_client.generate_schedule.return_value = mock_response
            MockClaudeClient.return_value = mock_client

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={
                    "week_start": week_start.isoformat(),
                    "clear_existing": True,
                },
            )

            assert response.status_code == 201
            data = response.json()

            # Should have only one schedule (new one)
            assert len(data["schedules"]) == 1
            assert float(data["schedules"][0]["allocated_hours"]) == 3.0

    @pytest.mark.asyncio
    async def test_generate_schedule_with_fixed_events(
        self, client: AsyncClient, sample_tasks
    ):
        """Test schedule generation with fixed events."""
        week_start = datetime.now() + timedelta(days=7)
        week_start_str = week_start.strftime("%Y-%m-%d")

        mock_response = f"""[
            {{"task_id": {sample_tasks[0].id}, "date": "{week_start_str}", "start_time": "09:00", "end_time": "12:00", "allocated_hours": 3.0}}
        ]"""

        with patch(
            "app.services.schedule_service.ClaudeClient"
        ) as MockClaudeClient:
            mock_client = AsyncMock()
            mock_client.generate_schedule.return_value = mock_response
            MockClaudeClient.return_value = mock_client

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={
                    "week_start": week_start.isoformat(),
                    "fixed_events": [
                        {
                            "date": week_start.isoformat(),
                            "start_time": "14:00",
                            "end_time": "16:00",
                            "title": "ゼミミーティング",
                        }
                    ],
                },
            )

            assert response.status_code == 201

            # Verify fixed events were passed to Claude
            call_args = mock_client.generate_schedule.call_args
            user_prompt = call_args[0][1]
            assert "ゼミミーティング" in user_prompt

    @pytest.mark.asyncio
    async def test_generate_schedule_invalid_json_response(
        self, client: AsyncClient, sample_tasks
    ):
        """Test handling of invalid JSON response from Claude."""
        week_start = datetime.now() + timedelta(days=7)

        with patch(
            "app.services.schedule_service.ClaudeClient"
        ) as MockClaudeClient:
            mock_client = AsyncMock()
            mock_client.generate_schedule.return_value = "This is not JSON"
            MockClaudeClient.return_value = mock_client

            response = await client.post(
                "/api/v1/workflow/schedule/generate-weekly",
                json={"week_start": week_start.isoformat()},
            )

            assert response.status_code == 422
            assert "パース" in response.json()["detail"]


class TestScheduleServiceUnit:
    """Unit tests for ScheduleService methods."""

    @pytest.mark.asyncio
    async def test_gather_schedulable_tasks(
        self, test_session, task_factory, time_entry_factory
    ):
        """Test gathering only schedulable tasks."""
        from app.services.schedule_service import ScheduleService

        # Create tasks with different statuses
        todo_task = await task_factory(
            name="Todo", status="todo", estimated_hours=Decimal("4.0")
        )
        doing_task = await task_factory(
            name="Doing", status="doing", estimated_hours=Decimal("4.0")
        )
        done_task = await task_factory(
            name="Done", status="done", estimated_hours=Decimal("4.0")
        )
        archive_task = await task_factory(
            name="Archive", status="archive", estimated_hours=Decimal("4.0")
        )

        # Add time entry to doing_task (partial completion)
        await time_entry_factory(
            task_id=doing_task.id,
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now(),
            duration_minutes=120,  # 2 hours
        )

        service = ScheduleService()
        week_end = datetime.now() + timedelta(days=7)
        tasks = await service._gather_schedulable_tasks(test_session, week_end)

        task_names = [t.name for t in tasks]
        assert "Todo" in task_names
        assert "Doing" in task_names
        assert "Done" not in task_names
        assert "Archive" not in task_names

        # Check remaining hours calculation
        doing_schedulable = next(t for t in tasks if t.name == "Doing")
        assert doing_schedulable.remaining_hours == Decimal("2.0")  # 4 - 2 = 2

    @pytest.mark.asyncio
    async def test_parse_schedule_response_with_code_block(
        self, task_factory
    ):
        """Test parsing response with markdown code blocks."""
        from app.services.schedule_service import ScheduleService

        task = await task_factory(name="Test Task", estimated_hours=Decimal("2.0"))

        response = f"""```json
[
    {{"task_id": {task.id}, "date": "2025-01-13", "allocated_hours": 2.0}}
]
```"""

        service = ScheduleService()
        entries = service._parse_schedule_response(
            response, [type("Task", (), {"id": task.id, "name": task.name})]
        )

        assert len(entries) == 1
        assert entries[0].task_id == task.id
        assert entries[0].allocated_hours == Decimal("2.0")
