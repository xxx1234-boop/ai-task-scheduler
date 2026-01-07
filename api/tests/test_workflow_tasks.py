"""
Tests for Task Workflow API endpoints.

This test file covers:
- Task breakdown (1 -> many) with time allocation
- Task merge (many -> 1)
- Bulk task creation with dependencies

Endpoints tested:
- POST /api/v1/workflow/tasks/breakdown - Break down task into subtasks
- POST /api/v1/workflow/tasks/merge - Merge multiple tasks into one
- POST /api/v1/workflow/tasks/bulk-create - Create multiple tasks with dependencies
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Task, TimeEntry, Schedule, TaskDependency
from tests.utils import assert_status_code


class TestTaskBreakdown:
    """Test POST /api/v1/workflow/tasks/breakdown"""

    async def test_breakdown_basic(self, client: AsyncClient, task_factory):
        """Test basic task breakdown."""
        # Arrange
        task = await task_factory(name="親タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1"},
                    {"name": "サブタスク2"},
                ],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["original_task"]["id"] == task.id
        assert len(data["created_tasks"]) == 2
        assert data["created_tasks"][0]["name"] == "サブタスク1"
        assert data["created_tasks"][1]["name"] == "サブタスク2"

    async def test_breakdown_creates_subtasks_with_parent_id(
        self, client: AsyncClient, task_factory, test_session: AsyncSession
    ):
        """Test that subtasks have parent_task_id set."""
        # Arrange
        task = await task_factory(name="親タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        subtask_id = data["created_tasks"][0]["id"]

        # Verify in database
        result = await test_session.execute(
            select(Task).where(Task.id == subtask_id)
        )
        subtask = result.scalar_one()
        assert subtask.parent_task_id == task.id

    async def test_breakdown_archives_original_when_flag_true(
        self, client: AsyncClient, task_factory, test_session: AsyncSession
    ):
        """Test that original task is archived when archive_original=true."""
        # Arrange
        task = await task_factory(name="親タスク", status="todo")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
                "archive_original": True,
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["original_task"]["status"] == "archive"

    async def test_breakdown_keeps_original_when_flag_false(
        self, client: AsyncClient, task_factory
    ):
        """Test that original task is kept when archive_original=false."""
        # Arrange
        task = await task_factory(name="親タスク", status="todo")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
                "archive_original": False,
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["original_task"]["status"] == "todo"

    async def test_breakdown_inherits_project_id(
        self, client: AsyncClient, project_factory, task_factory, test_session: AsyncSession
    ):
        """Test that subtasks inherit project_id from parent."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        task = await task_factory(name="親タスク", project_id=project.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        subtask_id = data["created_tasks"][0]["id"]

        result = await test_session.execute(
            select(Task).where(Task.id == subtask_id)
        )
        subtask = result.scalar_one()
        assert subtask.project_id == project.id

    async def test_breakdown_inherits_genre_id(
        self, client: AsyncClient, genre_factory, task_factory, test_session: AsyncSession
    ):
        """Test that subtasks inherit genre_id from parent when not specified."""
        # Arrange
        genre = await genre_factory(name="リサーチ")
        task = await task_factory(name="親タスク", genre_id=genre.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        subtask_id = data["created_tasks"][0]["id"]

        result = await test_session.execute(
            select(Task).where(Task.id == subtask_id)
        )
        subtask = result.scalar_one()
        assert subtask.genre_id == genre.id

    async def test_breakdown_with_depends_on_indices(
        self, client: AsyncClient, task_factory
    ):
        """Test breakdown with inter-subtask dependencies."""
        # Arrange
        task = await task_factory(name="親タスク")

        # Act - サブタスク2がサブタスク1に依存
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1", "depends_on_indices": []},
                    {"name": "サブタスク2", "depends_on_indices": [0]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        # dependencies_transferred includes inter-subtask dependencies
        assert data["dependencies_transferred"] >= 1

    async def test_breakdown_allocates_time_entries_proportionally(
        self, client: AsyncClient, task_factory, time_entry_factory, test_session: AsyncSession
    ):
        """Test that TimeEntries are allocated proportionally."""
        # Arrange
        task = await task_factory(name="親タスク")
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now() - timedelta(hours=1),
            duration_minutes=60,
        )

        # Act - 2 subtasks with equal estimated_hours
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1", "estimated_hours": "1.0"},
                    {"name": "サブタスク2", "estimated_hours": "1.0"},
                ],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["allocation_summary"]["time_entries_allocated"] == 2
        # 60 minutes split equally = 30 each
        assert data["allocation_summary"]["total_time_minutes_allocated"] == 60

    async def test_breakdown_allocates_schedules_proportionally(
        self, client: AsyncClient, task_factory, schedule_factory, test_session: AsyncSession
    ):
        """Test that Schedules are allocated proportionally."""
        # Arrange
        task = await task_factory(name="親タスク")
        await schedule_factory(
            task_id=task.id,
            scheduled_date=datetime.now().date(),
            allocated_hours=Decimal("2.0"),
        )

        # Act - 2 subtasks with 1:3 ratio
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1", "estimated_hours": "1.0"},
                    {"name": "サブタスク2", "estimated_hours": "3.0"},
                ],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["allocation_summary"]["schedules_allocated"] == 2
        # 2.0 hours split 1:3 = 0.5 + 1.5 = 2.0
        assert float(data["allocation_summary"]["total_schedule_hours_allocated"]) == 2.0

    async def test_breakdown_with_manual_allocated_hours(
        self, client: AsyncClient, task_factory, time_entry_factory
    ):
        """Test breakdown with manual allocated_hours override."""
        # Arrange
        task = await task_factory(name="親タスク")
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now() - timedelta(hours=1),
            duration_minutes=100,
        )

        # Act - Manual allocation: 30:70 ratio
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1", "allocated_hours": "0.3"},
                    {"name": "サブタスク2", "allocated_hours": "0.7"},
                ],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["allocation_summary"]["time_entries_allocated"] == 2

    async def test_breakdown_allocation_summary_in_response(
        self, client: AsyncClient, task_factory, time_entry_factory, schedule_factory
    ):
        """Test that allocation_summary is included in response."""
        # Arrange
        task = await task_factory(name="親タスク")
        await time_entry_factory(
            task_id=task.id,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_minutes=60,
        )
        await schedule_factory(
            task_id=task.id,
            scheduled_date=datetime.now().date(),
            allocated_hours=Decimal("1.0"),
        )

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        summary = data["allocation_summary"]
        assert "time_entries_allocated" in summary
        assert "schedules_allocated" in summary
        assert "total_time_minutes_allocated" in summary
        assert "total_schedule_hours_allocated" in summary

    async def test_breakdown_task_not_found(self, client: AsyncClient):
        """Test breakdown with non-existent task."""
        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": 99999,
                "subtasks": [{"name": "サブタスク1"}],
            },
        )

        # Assert
        assert_status_code(response, 404)

    async def test_breakdown_archived_task_fails(
        self, client: AsyncClient, task_factory
    ):
        """Test that archived task cannot be broken down."""
        # Arrange
        task = await task_factory(name="アーカイブタスク", status="archive")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [{"name": "サブタスク1"}],
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "archived" in response.json()["detail"].lower()

    async def test_breakdown_task_with_children_fails(
        self, client: AsyncClient, task_factory
    ):
        """Test that task with existing children cannot be broken down."""
        # Arrange
        parent = await task_factory(name="親タスク")
        await task_factory(name="既存子タスク", parent_task_id=parent.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": parent.id,
                "subtasks": [{"name": "新サブタスク"}],
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "child" in response.json()["detail"].lower()

    async def test_breakdown_empty_subtasks_fails(
        self, client: AsyncClient, task_factory
    ):
        """Test that breakdown with empty subtasks fails."""
        # Arrange
        task = await task_factory(name="タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [],
            },
        )

        # Assert
        assert_status_code(response, 422)

    async def test_breakdown_invalid_depends_on_index(
        self, client: AsyncClient, task_factory
    ):
        """Test that invalid depends_on_indices is rejected."""
        # Arrange
        task = await task_factory(name="タスク")

        # Act - Index 5 is out of range for 2 subtasks
        response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1"},
                    {"name": "サブタスク2", "depends_on_indices": [5]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "out of range" in response.json()["detail"].lower()


class TestTaskMerge:
    """Test POST /api/v1/workflow/tasks/merge"""

    async def test_merge_basic(self, client: AsyncClient, task_factory):
        """Test basic task merge."""
        # Arrange
        task1 = await task_factory(name="タスク1")
        task2 = await task_factory(name="タスク2")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task1.id, task2.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["merged_task"]["name"] == "統合タスク"
        assert len(data["archived_tasks"]) == 2
        assert task1.id in data["archived_tasks"]
        assert task2.id in data["archived_tasks"]

    async def test_merge_archives_source_tasks(
        self, client: AsyncClient, task_factory, test_session: AsyncSession
    ):
        """Test that source tasks are archived after merge."""
        # Arrange
        task1 = await task_factory(name="タスク1", status="todo")
        task2 = await task_factory(name="タスク2", status="doing")

        # Act
        await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task1.id, task2.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Verify
        result1 = await test_session.execute(select(Task).where(Task.id == task1.id))
        result2 = await test_session.execute(select(Task).where(Task.id == task2.id))

        # Need to refresh from db
        await test_session.refresh(task1)
        await test_session.refresh(task2)

        assert task1.status == "archive"
        assert task2.status == "archive"

    async def test_merge_transfers_time_entries(
        self, client: AsyncClient, task_factory, time_entry_factory, test_session: AsyncSession
    ):
        """Test that TimeEntries are transferred to merged task."""
        # Arrange
        task1 = await task_factory(name="タスク1")
        task2 = await task_factory(name="タスク2")
        await time_entry_factory(task_id=task1.id, duration_minutes=30)
        await time_entry_factory(task_id=task2.id, duration_minutes=45)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task1.id, task2.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["time_entries_transferred"] == 2

    async def test_merge_transfers_schedules(
        self, client: AsyncClient, task_factory, schedule_factory, test_session: AsyncSession
    ):
        """Test that Schedules are transferred to merged task."""
        # Arrange
        task1 = await task_factory(name="タスク1")
        task2 = await task_factory(name="タスク2")
        await schedule_factory(task_id=task1.id)
        await schedule_factory(task_id=task2.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task1.id, task2.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        merged_task_id = data["merged_task"]["id"]

        # Verify schedules transferred
        result = await test_session.execute(
            select(Schedule).where(Schedule.task_id == merged_task_id)
        )
        schedules = result.scalars().all()
        assert len(schedules) == 2

    async def test_merge_single_task_fails(self, client: AsyncClient, task_factory):
        """Test that merging single task fails."""
        # Arrange
        task = await task_factory(name="タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "at least 2" in response.json()["detail"].lower()

    async def test_merge_task_not_found(self, client: AsyncClient, task_factory):
        """Test merge with non-existent task."""
        # Arrange
        task = await task_factory(name="タスク")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task.id, 99999],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 404)

    async def test_merge_different_projects_fails(
        self, client: AsyncClient, project_factory, task_factory
    ):
        """Test that merging tasks from different projects fails."""
        # Arrange
        project1 = await project_factory(name="プロジェクト1")
        project2 = await project_factory(name="プロジェクト2")
        task1 = await task_factory(name="タスク1", project_id=project1.id)
        task2 = await task_factory(name="タスク2", project_id=project2.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task1.id, task2.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "same project" in response.json()["detail"].lower()

    async def test_merge_inherits_project_from_sources(
        self, client: AsyncClient, project_factory, task_factory, test_session: AsyncSession
    ):
        """Test that merged task inherits project from source tasks."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        task1 = await task_factory(name="タスク1", project_id=project.id)
        task2 = await task_factory(name="タスク2", project_id=project.id)

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": [task1.id, task2.id],
                "merged_task": {"name": "統合タスク"},
            },
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        merged_task_id = data["merged_task"]["id"]

        result = await test_session.execute(
            select(Task).where(Task.id == merged_task_id)
        )
        merged_task = result.scalar_one()
        assert merged_task.project_id == project.id


class TestBulkCreate:
    """Test POST /api/v1/workflow/tasks/bulk-create"""

    async def test_bulk_create_basic(self, client: AsyncClient):
        """Test basic bulk task creation."""
        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスク1"},
                    {"name": "タスク2"},
                    {"name": "タスク3"},
                ],
            },
        )

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert len(data["created_tasks"]) == 3
        assert data["created_tasks"][0]["name"] == "タスク1"
        assert data["created_tasks"][1]["name"] == "タスク2"
        assert data["created_tasks"][2]["name"] == "タスク3"

    async def test_bulk_create_with_project_id(
        self, client: AsyncClient, project_factory, test_session: AsyncSession
    ):
        """Test bulk create with project_id."""
        # Arrange
        project = await project_factory(name="プロジェクト")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "project_id": project.id,
                "tasks": [
                    {"name": "タスク1"},
                    {"name": "タスク2"},
                ],
            },
        )

        # Assert
        assert_status_code(response, 201)
        data = response.json()

        # Verify project_id
        for task_summary in data["created_tasks"]:
            result = await test_session.execute(
                select(Task).where(Task.id == task_summary["id"])
            )
            task = result.scalar_one()
            assert task.project_id == project.id

    async def test_bulk_create_with_dependencies(self, client: AsyncClient):
        """Test bulk create with inter-task dependencies."""
        # Act - Task2 depends on Task1
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスク1"},
                    {"name": "タスク2", "depends_on_indices": [0]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["dependencies_created"] == 1

    async def test_bulk_create_chain_dependencies(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test bulk create with chain dependencies (A -> B -> C)."""
        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスクA"},
                    {"name": "タスクB", "depends_on_indices": [0]},
                    {"name": "タスクC", "depends_on_indices": [1]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["dependencies_created"] == 2

        # Verify chain
        task_a_id = data["created_tasks"][0]["id"]
        task_b_id = data["created_tasks"][1]["id"]
        task_c_id = data["created_tasks"][2]["id"]

        # B depends on A
        result = await test_session.execute(
            select(TaskDependency).where(
                TaskDependency.task_id == task_b_id,
                TaskDependency.depends_on_task_id == task_a_id,
            )
        )
        assert result.scalar_one_or_none() is not None

        # C depends on B
        result = await test_session.execute(
            select(TaskDependency).where(
                TaskDependency.task_id == task_c_id,
                TaskDependency.depends_on_task_id == task_b_id,
            )
        )
        assert result.scalar_one_or_none() is not None

    async def test_bulk_create_empty_tasks_fails(self, client: AsyncClient):
        """Test that bulk create with empty tasks fails."""
        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={"tasks": []},
        )

        # Assert
        assert_status_code(response, 422)

    async def test_bulk_create_self_dependency_fails(self, client: AsyncClient):
        """Test that self-dependency is rejected."""
        # Act - Task depends on itself
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスク1", "depends_on_indices": [0]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "itself" in response.json()["detail"].lower()

    async def test_bulk_create_cycle_fails(self, client: AsyncClient):
        """Test that cycle in dependencies is rejected."""
        # Act - A -> B -> A (cycle)
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスクA", "depends_on_indices": [1]},
                    {"name": "タスクB", "depends_on_indices": [0]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "cycle" in response.json()["detail"].lower()

    async def test_bulk_create_invalid_index_fails(self, client: AsyncClient):
        """Test that invalid index is rejected."""
        # Act - Index 5 is out of range
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスク1"},
                    {"name": "タスク2", "depends_on_indices": [5]},
                ],
            },
        )

        # Assert
        assert_status_code(response, 422)
        assert "out of range" in response.json()["detail"].lower()

    async def test_bulk_create_with_all_fields(
        self, client: AsyncClient, genre_factory, test_session: AsyncSession
    ):
        """Test bulk create with all optional fields."""
        # Arrange
        genre = await genre_factory(name="リサーチ")

        # Act
        response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {
                        "name": "フルタスク",
                        "genre_id": genre.id,
                        "estimated_hours": "5.5",
                        "priority": "高",
                        "want_level": "高",
                    },
                ],
            },
        )

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        task_id = data["created_tasks"][0]["id"]

        result = await test_session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one()
        assert task.genre_id == genre.id
        assert task.estimated_hours == Decimal("5.5")
        assert task.priority == "高"
        assert task.want_level == "高"


class TestWorkflowIntegration:
    """Test workflow integration scenarios."""

    async def test_breakdown_then_merge(
        self, client: AsyncClient, task_factory
    ):
        """Test breaking down a task then merging subtasks back."""
        # Arrange - Create and breakdown
        task = await task_factory(name="親タスク")

        breakdown_response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task.id,
                "subtasks": [
                    {"name": "サブタスク1"},
                    {"name": "サブタスク2"},
                ],
                "archive_original": False,
            },
        )
        assert_status_code(breakdown_response, 200)
        subtask_ids = [t["id"] for t in breakdown_response.json()["created_tasks"]]

        # Act - Merge subtasks back
        merge_response = await client.post(
            "/api/v1/workflow/tasks/merge",
            json={
                "task_ids": subtask_ids,
                "merged_task": {"name": "再統合タスク"},
            },
        )

        # Assert
        assert_status_code(merge_response, 200)
        data = merge_response.json()
        assert data["merged_task"]["name"] == "再統合タスク"
        assert len(data["archived_tasks"]) == 2

    async def test_bulk_create_then_breakdown(
        self, client: AsyncClient
    ):
        """Test bulk creating tasks then breaking one down."""
        # Arrange - Bulk create
        bulk_response = await client.post(
            "/api/v1/workflow/tasks/bulk-create",
            json={
                "tasks": [
                    {"name": "タスクA"},
                    {"name": "タスクB"},
                ],
            },
        )
        assert_status_code(bulk_response, 201)
        task_a_id = bulk_response.json()["created_tasks"][0]["id"]

        # Act - Breakdown task A
        breakdown_response = await client.post(
            "/api/v1/workflow/tasks/breakdown",
            json={
                "task_id": task_a_id,
                "subtasks": [
                    {"name": "タスクA-1"},
                    {"name": "タスクA-2"},
                ],
            },
        )

        # Assert
        assert_status_code(breakdown_response, 200)
        data = breakdown_response.json()
        assert len(data["created_tasks"]) == 2
