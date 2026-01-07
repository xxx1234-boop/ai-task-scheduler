"""
Tests for Tasks CRUD API endpoints.

This is the most complex test file, covering:
- Standard CRUD operations
- Hierarchical task relationships (parent/child with parent_task_id)
- Advanced filtering (project_id, genre_id, status, priority, has_parent, parent_task_id)
- Foreign key constraints (tasks.project_id, tasks.genre_id, tasks.parent_task_id)
- Specialized endpoints (GET /tasks/{id}/children)

Endpoints tested:
- POST /api/v1/tasks - Create task
- GET /api/v1/tasks - List tasks with filtering
- GET /api/v1/tasks/{id} - Get single task
- GET /api/v1/tasks/{id}/children - Get child tasks
- PATCH /api/v1/tasks/{id} - Update task
- DELETE /api/v1/tasks/{id} - Delete task
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Project, Task
from tests.utils import (
    assert_pagination_structure,
    assert_status_code,
    assert_validation_error,
    get_record_by_id,
    record_exists,
)


class TestTaskCRUD:
    """Test standard CRUD operations for tasks."""

    async def test_create_task_minimal(self, client: AsyncClient):
        """Test creating task with only required fields."""
        # Arrange
        task_data = {"name": "研究タスク"}

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["name"] == "研究タスク"
        assert data["status"] == "todo"  # Default value
        assert data["priority"] == "中"  # Default value
        assert "id" in data

    async def test_create_task_with_project_and_genre(
        self, client: AsyncClient, project_factory, genre_factory
    ):
        """Test creating task with project and genre references."""
        # Arrange
        project = await project_factory(name="プロジェクトA")
        genre = await genre_factory(name="リサーチ")
        task_data = {
            "name": "タスク1",
            "project_id": project.id,
            "genre_id": genre.id,
        }

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["project_id"] == project.id
        assert data["genre_id"] == genre.id

    async def test_create_task_with_all_fields(self, client: AsyncClient):
        """Test creating task with all optional fields."""
        # Arrange
        task_data = {
            "name": "完全なタスク",
            "status": "doing",
            "priority": "高",
            "want_level": "高",
            "estimated_hours": "5.5",
            "recurrence": "毎日",
            "is_splittable": True,
            "note": "テストメモ",
        }

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["name"] == "完全なタスク"
        assert data["status"] == "doing"
        assert data["priority"] == "高"
        assert data["want_level"] == "高"
        assert data["note"] == "テストメモ"

    async def test_create_task_missing_name(self, client: AsyncClient):
        """Test that creating task without name fails."""
        # Arrange
        task_data = {"status": "todo"}

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert_validation_error(response)

    async def test_list_tasks_empty(self, client: AsyncClient):
        """Test listing tasks when database is empty."""
        # Act
        response = await client.get("/api/v1/tasks")

        # Assert
        assert_pagination_structure(response, expected_total=0)

    async def test_list_tasks_with_data(self, client: AsyncClient, task_factory):
        """Test listing multiple tasks."""
        # Arrange
        await task_factory(name="タスク1")
        await task_factory(name="タスク2")
        await task_factory(name="タスク3")

        # Act
        response = await client.get("/api/v1/tasks")

        # Assert
        assert_pagination_structure(response, expected_total=3)

    async def test_get_task_by_id(self, client: AsyncClient, task_factory):
        """Test getting a single task by ID."""
        # Arrange
        task = await task_factory(name="テストタスク", priority="高")

        # Act
        response = await client.get(f"/api/v1/tasks/{task.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["id"] == task.id
        assert data["name"] == "テストタスク"
        assert data["priority"] == "高"

    async def test_get_task_not_found(self, client: AsyncClient):
        """Test getting non-existent task returns 404."""
        # Act
        response = await client.get("/api/v1/tasks/99999")

        # Assert
        assert_status_code(response, 404)

    async def test_update_task_status(self, client: AsyncClient, task_factory):
        """Test updating task status."""
        # Arrange
        task = await task_factory(name="タスク", status="todo")

        # Act
        update_data = {"status": "doing"}
        response = await client.patch(f"/api/v1/tasks/{task.id}", json=update_data)

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["status"] == "doing"

    async def test_update_task_multiple_fields(
        self, client: AsyncClient, task_factory
    ):
        """Test updating multiple task fields at once."""
        # Arrange
        task = await task_factory(name="Old", priority="低", want_level="低")

        # Act
        update_data = {"name": "New", "priority": "高", "want_level": "高"}
        response = await client.patch(f"/api/v1/tasks/{task.id}", json=update_data)

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["name"] == "New"
        assert data["priority"] == "高"
        assert data["want_level"] == "高"

    async def test_delete_task(
        self, client: AsyncClient, task_factory, test_session: AsyncSession
    ):
        """Test deleting a task."""
        # Arrange
        task = await task_factory(name="削除予定")
        task_id = task.id

        # Act
        response = await client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert_status_code(response, 204)

        # Verify deletion
        exists = await record_exists(test_session, Task, task_id)
        assert not exists


class TestTaskFiltering:
    """Test advanced filtering capabilities for task listings."""

    async def test_filter_by_project_id(
        self, client: AsyncClient, task_factory, project_factory
    ):
        """Test filtering tasks by project_id."""
        # Arrange
        project1 = await project_factory(name="プロジェクト1")
        project2 = await project_factory(name="プロジェクト2")

        task1 = await task_factory(name="タスク1", project_id=project1.id)
        task2 = await task_factory(name="タスク2", project_id=project1.id)
        task3 = await task_factory(name="タスク3", project_id=project2.id)

        # Act
        response = await client.get(f"/api/v1/tasks?project_id={project1.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        task_ids = [item["id"] for item in data["items"]]
        assert task1.id in task_ids
        assert task2.id in task_ids
        assert task3.id not in task_ids

    async def test_filter_by_genre_id(
        self, client: AsyncClient, task_factory, genre_factory
    ):
        """Test filtering tasks by genre_id."""
        # Arrange
        genre1 = await genre_factory(name="リサーチ")
        genre2 = await genre_factory(name="コーディング")

        task1 = await task_factory(name="タスク1", genre_id=genre1.id)
        task2 = await task_factory(name="タスク2", genre_id=genre2.id)

        # Act
        response = await client.get(f"/api/v1/tasks?genre_id={genre1.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == task1.id

    async def test_filter_by_status(self, client: AsyncClient, task_factory):
        """Test filtering tasks by status."""
        # Arrange
        await task_factory(name="Todo1", status="todo")
        await task_factory(name="Todo2", status="todo")
        await task_factory(name="Doing", status="doing")
        await task_factory(name="Done", status="done")

        # Act
        response = await client.get("/api/v1/tasks?status=todo")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        assert all(item["status"] == "todo" for item in data["items"])

    async def test_filter_by_priority(self, client: AsyncClient, task_factory):
        """Test filtering tasks by priority."""
        # Arrange
        await task_factory(name="高優先度1", priority="高")
        await task_factory(name="高優先度2", priority="高")
        await task_factory(name="中優先度", priority="中")
        await task_factory(name="低優先度", priority="低")

        # Act
        response = await client.get("/api/v1/tasks?priority=高")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        assert all(item["priority"] == "高" for item in data["items"])

    async def test_filter_by_has_parent_true(
        self, client: AsyncClient, task_factory
    ):
        """Test filtering tasks that have parent (subtasks)."""
        # Arrange
        parent = await task_factory(name="親タスク", parent_task_id=None)
        child1 = await task_factory(name="子タスク1", parent_task_id=parent.id)
        child2 = await task_factory(name="子タスク2", parent_task_id=parent.id)
        standalone = await task_factory(name="独立タスク", parent_task_id=None)

        # Act
        response = await client.get("/api/v1/tasks?has_parent=true")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        task_ids = [item["id"] for item in data["items"]]
        assert child1.id in task_ids
        assert child2.id in task_ids
        assert parent.id not in task_ids
        assert standalone.id not in task_ids

    async def test_filter_by_has_parent_false(
        self, client: AsyncClient, task_factory
    ):
        """Test filtering tasks without parent (top-level tasks)."""
        # Arrange
        parent = await task_factory(name="親タスク", parent_task_id=None)
        child = await task_factory(name="子タスク", parent_task_id=parent.id)
        standalone = await task_factory(name="独立タスク", parent_task_id=None)

        # Act
        response = await client.get("/api/v1/tasks?has_parent=false")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        task_ids = [item["id"] for item in data["items"]]
        assert parent.id in task_ids
        assert standalone.id in task_ids
        assert child.id not in task_ids

    async def test_filter_by_parent_task_id(
        self, client: AsyncClient, task_factory
    ):
        """Test filtering tasks by specific parent_task_id."""
        # Arrange
        parent1 = await task_factory(name="親1")
        parent2 = await task_factory(name="親2")
        child1a = await task_factory(name="子1-A", parent_task_id=parent1.id)
        child1b = await task_factory(name="子1-B", parent_task_id=parent1.id)
        child2 = await task_factory(name="子2", parent_task_id=parent2.id)

        # Act
        response = await client.get(f"/api/v1/tasks?parent_task_id={parent1.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 2
        task_ids = [item["id"] for item in data["items"]]
        assert child1a.id in task_ids
        assert child1b.id in task_ids
        assert child2.id not in task_ids

    async def test_filter_combined_filters(
        self, client: AsyncClient, task_factory, project_factory
    ):
        """Test combining multiple filters."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        await task_factory(
            name="対象タスク", project_id=project.id, status="todo", priority="高"
        )
        await task_factory(
            name="除外1", project_id=project.id, status="done", priority="高"
        )
        await task_factory(
            name="除外2", project_id=project.id, status="todo", priority="低"
        )

        # Act
        response = await client.get(
            f"/api/v1/tasks?project_id={project.id}&status=todo&priority=高"
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "対象タスク"


class TestTaskHierarchy:
    """Test hierarchical task relationships (parent/child)."""

    async def test_create_subtask(
        self, client: AsyncClient, task_factory
    ):
        """Test creating a subtask with parent_task_id."""
        # Arrange
        parent = await task_factory(name="親タスク")
        subtask_data = {
            "name": "サブタスク",
            "parent_task_id": parent.id,
            "decomposition_level": 1,
        }

        # Act
        response = await client.post("/api/v1/tasks", json=subtask_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["parent_task_id"] == parent.id
        assert data["decomposition_level"] == 1

    async def test_get_task_children(
        self, client: AsyncClient, task_factory
    ):
        """Test specialized endpoint GET /tasks/{id}/children."""
        # Arrange
        parent = await task_factory(name="親タスク")
        child1 = await task_factory(name="子1", parent_task_id=parent.id)
        child2 = await task_factory(name="子2", parent_task_id=parent.id)
        child3 = await task_factory(name="子3", parent_task_id=parent.id)

        # Create another parent to ensure filtering works
        other_parent = await task_factory(name="別の親")
        other_child = await task_factory(name="別の子", parent_task_id=other_parent.id)

        # Act
        response = await client.get(f"/api/v1/tasks/{parent.id}/children")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data) == 3
        child_ids = [item["id"] for item in data]
        assert child1.id in child_ids
        assert child2.id in child_ids
        assert child3.id in child_ids
        assert other_child.id not in child_ids

    async def test_get_children_of_task_without_children(
        self, client: AsyncClient, task_factory
    ):
        """Test getting children of task that has no children."""
        # Arrange
        parent = await task_factory(name="親（子なし）")

        # Act
        response = await client.get(f"/api/v1/tasks/{parent.id}/children")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data == []

    async def test_delete_parent_task_sets_children_parent_to_null(
        self, client: AsyncClient, task_factory, test_session: AsyncSession
    ):
        """Test ON DELETE SET NULL constraint when parent is deleted."""
        # Arrange
        parent = await task_factory(name="親タスク")
        child = await task_factory(name="子タスク", parent_task_id=parent.id)

        # Act: Delete parent
        response = await client.delete(f"/api/v1/tasks/{parent.id}")

        # Assert
        assert_status_code(response, 204)

        # Verify child still exists but parent_task_id is NULL
        await test_session.refresh(child)
        assert child.parent_task_id is None


class TestTaskForeignKeys:
    """Test foreign key constraint behaviors."""

    async def test_create_task_with_invalid_project_id(self, client: AsyncClient):
        """Test creating task with non-existent project_id."""
        # Arrange
        task_data = {
            "name": "タスク",
            "project_id": 99999,  # Non-existent
        }

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        # Foreign key constraint violation should return error
        assert response.status_code in [400, 422, 500]

    async def test_create_task_with_invalid_genre_id(self, client: AsyncClient):
        """Test creating task with non-existent genre_id."""
        # Arrange
        task_data = {
            "name": "タスク",
            "genre_id": 99999,  # Non-existent
        }

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code in [400, 422, 500]

    async def test_delete_project_sets_task_project_id_to_null(
        self, client: AsyncClient, project_factory, task_factory, test_session: AsyncSession
    ):
        """Test ON DELETE SET NULL when project is deleted."""
        # Arrange
        project = await project_factory(name="プロジェクト")
        task = await task_factory(name="タスク", project_id=project.id)

        # Act: Delete project
        response = await client.delete(f"/api/v1/projects/{project.id}")

        # Assert
        assert_status_code(response, 204)

        # Verify task still exists but project_id is NULL
        await test_session.refresh(task)
        assert task.project_id is None

    async def test_delete_genre_sets_task_genre_id_to_null(
        self, client: AsyncClient, genre_factory, task_factory, test_session: AsyncSession
    ):
        """Test ON DELETE SET NULL when genre is deleted."""
        # Arrange
        genre = await genre_factory(name="ジャンル")
        task = await task_factory(name="タスク", genre_id=genre.id)

        # Act: Delete genre
        response = await client.delete(f"/api/v1/genres/{genre.id}")

        # Assert
        assert_status_code(response, 204)

        # Verify task still exists but genre_id is NULL
        await test_session.refresh(task)
        assert task.genre_id is None


class TestTaskValidation:
    """Test validation rules for task fields."""

    async def test_create_task_with_invalid_status(self, client: AsyncClient):
        """Test creating task with invalid status value."""
        # Arrange
        task_data = {
            "name": "タスク",
            "status": "invalid_status",  # Not in allowed values
        }

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        # Should fail validation (depends on model validation implementation)
        assert response.status_code in [422, 500]

    async def test_create_task_with_invalid_priority(self, client: AsyncClient):
        """Test creating task with invalid priority value."""
        # Arrange
        task_data = {
            "name": "タスク",
            "priority": "invalid",  # Not in 高/中/低
        }

        # Act
        response = await client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code in [422, 500]
