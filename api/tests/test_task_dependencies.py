"""
Tests for Task Dependencies API endpoints.

This test file covers:
- Getting task dependencies (depends_on and blocking)
- Adding dependencies with cycle detection
- Removing dependencies

Endpoints tested:
- GET /api/v1/tasks/{id}/dependencies - Get task dependencies
- POST /api/v1/tasks/{id}/dependencies - Add dependency
- DELETE /api/v1/tasks/{id}/dependencies/{dep_id} - Remove dependency
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.utils import assert_status_code


class TestGetDependencies:
    """Test GET /api/v1/tasks/{id}/dependencies"""

    async def test_get_dependencies_empty(self, client: AsyncClient, task_factory):
        """Test getting dependencies for task with no dependencies."""
        # Arrange
        task = await task_factory(name="独立タスク")

        # Act
        response = await client.get(f"/api/v1/tasks/{task.id}/dependencies")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["depends_on"] == []
        assert data["blocking"] == []

    async def test_get_dependencies_with_depends_on(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test getting tasks that this task depends on."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        # B depends on A (A must be done before B)
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)

        # Act
        response = await client.get(f"/api/v1/tasks/{task_b.id}/dependencies")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["depends_on"]) == 1
        assert data["depends_on"][0]["id"] == task_a.id
        assert data["depends_on"][0]["name"] == "タスクA"
        assert data["blocking"] == []

    async def test_get_dependencies_with_blocking(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test getting tasks that are blocked by this task."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        # B depends on A, so A is blocking B
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)

        # Act
        response = await client.get(f"/api/v1/tasks/{task_a.id}/dependencies")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["depends_on"] == []
        assert len(data["blocking"]) == 1
        assert data["blocking"][0]["id"] == task_b.id
        assert data["blocking"][0]["name"] == "タスクB"

    async def test_get_dependencies_both_directions(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test task with both depends_on and blocking relationships."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        task_c = await task_factory(name="タスクC")
        # A -> B -> C (B depends on A, C depends on B)
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)
        await task_dependency_factory(task_id=task_c.id, depends_on_task_id=task_b.id)

        # Act
        response = await client.get(f"/api/v1/tasks/{task_b.id}/dependencies")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["depends_on"]) == 1
        assert data["depends_on"][0]["id"] == task_a.id
        assert len(data["blocking"]) == 1
        assert data["blocking"][0]["id"] == task_c.id

    async def test_get_dependencies_task_not_found(self, client: AsyncClient):
        """Test getting dependencies for non-existent task."""
        # Act
        response = await client.get("/api/v1/tasks/99999/dependencies")

        # Assert
        assert_status_code(response, 404)

    async def test_get_dependencies_multiple_deps(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test task depending on multiple tasks."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        task_c = await task_factory(name="タスクC")
        # C depends on both A and B
        await task_dependency_factory(task_id=task_c.id, depends_on_task_id=task_a.id)
        await task_dependency_factory(task_id=task_c.id, depends_on_task_id=task_b.id)

        # Act
        response = await client.get(f"/api/v1/tasks/{task_c.id}/dependencies")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert len(data["depends_on"]) == 2
        dep_ids = [d["id"] for d in data["depends_on"]]
        assert task_a.id in dep_ids
        assert task_b.id in dep_ids


class TestAddDependency:
    """Test POST /api/v1/tasks/{id}/dependencies"""

    async def test_add_dependency_success(self, client: AsyncClient, task_factory):
        """Test successfully adding a dependency."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")

        # Act
        response = await client.post(
            f"/api/v1/tasks/{task_b.id}/dependencies",
            json={"depends_on_task_id": task_a.id},
        )

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["message"] == "Dependency added successfully"

    async def test_add_dependency_creates_record(
        self, client: AsyncClient, task_factory
    ):
        """Test that adding dependency creates the relationship."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")

        # Act
        await client.post(
            f"/api/v1/tasks/{task_b.id}/dependencies",
            json={"depends_on_task_id": task_a.id},
        )

        # Verify by getting dependencies
        response = await client.get(f"/api/v1/tasks/{task_b.id}/dependencies")

        # Assert
        data = response.json()
        assert len(data["depends_on"]) == 1
        assert data["depends_on"][0]["id"] == task_a.id

    async def test_add_dependency_self_reference(self, client: AsyncClient, task_factory):
        """Test that self-reference is rejected."""
        # Arrange
        task = await task_factory(name="タスク")

        # Act
        response = await client.post(
            f"/api/v1/tasks/{task.id}/dependencies",
            json={"depends_on_task_id": task.id},
        )

        # Assert
        assert_status_code(response, 422)
        assert "cannot depend on itself" in response.json()["detail"].lower()

    async def test_add_dependency_task_not_found(self, client: AsyncClient, task_factory):
        """Test adding dependency when task doesn't exist."""
        # Arrange
        task_a = await task_factory(name="タスクA")

        # Act
        response = await client.post(
            "/api/v1/tasks/99999/dependencies",
            json={"depends_on_task_id": task_a.id},
        )

        # Assert
        assert_status_code(response, 404)

    async def test_add_dependency_depends_on_not_found(
        self, client: AsyncClient, task_factory
    ):
        """Test adding dependency when depends_on task doesn't exist."""
        # Arrange
        task_a = await task_factory(name="タスクA")

        # Act
        response = await client.post(
            f"/api/v1/tasks/{task_a.id}/dependencies",
            json={"depends_on_task_id": 99999},
        )

        # Assert
        assert_status_code(response, 404)

    async def test_add_dependency_cycle_direct(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test that direct cycle (A -> B -> A) is rejected."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        # B depends on A
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)

        # Act - Try to make A depend on B (would create cycle)
        response = await client.post(
            f"/api/v1/tasks/{task_a.id}/dependencies",
            json={"depends_on_task_id": task_b.id},
        )

        # Assert
        assert_status_code(response, 422)
        assert "cycle" in response.json()["detail"].lower()

    async def test_add_dependency_cycle_indirect(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test that indirect cycle (A -> B -> C -> A) is rejected."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        task_c = await task_factory(name="タスクC")
        # A -> B -> C
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)
        await task_dependency_factory(task_id=task_c.id, depends_on_task_id=task_b.id)

        # Act - Try to make A depend on C (would create cycle A -> B -> C -> A)
        response = await client.post(
            f"/api/v1/tasks/{task_a.id}/dependencies",
            json={"depends_on_task_id": task_c.id},
        )

        # Assert
        assert_status_code(response, 422)
        assert "cycle" in response.json()["detail"].lower()

    async def test_add_dependency_no_false_cycle_detection(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test that valid dependencies are not rejected as cycles."""
        # Arrange: A -> B, A -> C (fan-out pattern, no cycle)
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        task_c = await task_factory(name="タスクC")
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)

        # Act - Add C depending on A (valid, no cycle)
        response = await client.post(
            f"/api/v1/tasks/{task_c.id}/dependencies",
            json={"depends_on_task_id": task_a.id},
        )

        # Assert
        assert_status_code(response, 201)


class TestRemoveDependency:
    """Test DELETE /api/v1/tasks/{id}/dependencies/{dep_id}"""

    async def test_remove_dependency_success(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test successfully removing a dependency."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)

        # Act
        response = await client.delete(
            f"/api/v1/tasks/{task_b.id}/dependencies/{task_a.id}"
        )

        # Assert
        assert_status_code(response, 204)

    async def test_remove_dependency_actually_removes(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test that removing dependency actually removes the relationship."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)

        # Act
        await client.delete(f"/api/v1/tasks/{task_b.id}/dependencies/{task_a.id}")

        # Verify
        response = await client.get(f"/api/v1/tasks/{task_b.id}/dependencies")

        # Assert
        data = response.json()
        assert data["depends_on"] == []

    async def test_remove_dependency_not_found(
        self, client: AsyncClient, task_factory
    ):
        """Test removing non-existent dependency."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        # No dependency created

        # Act
        response = await client.delete(
            f"/api/v1/tasks/{task_b.id}/dependencies/{task_a.id}"
        )

        # Assert
        assert_status_code(response, 404)

    async def test_remove_dependency_task_not_found(self, client: AsyncClient):
        """Test removing dependency from non-existent task."""
        # Act
        response = await client.delete("/api/v1/tasks/99999/dependencies/1")

        # Assert
        assert_status_code(response, 404)


class TestDependencyChainScenarios:
    """Test complex dependency chain scenarios."""

    async def test_deep_dependency_chain(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test deep dependency chain (A -> B -> C -> D -> E)."""
        # Arrange
        tasks = []
        for i in range(5):
            task = await task_factory(name=f"タスク{i}")
            tasks.append(task)

        # Create chain: 0 -> 1 -> 2 -> 3 -> 4
        for i in range(1, 5):
            await task_dependency_factory(
                task_id=tasks[i].id, depends_on_task_id=tasks[i - 1].id
            )

        # Act - Try to make first depend on last (would create cycle)
        response = await client.post(
            f"/api/v1/tasks/{tasks[0].id}/dependencies",
            json={"depends_on_task_id": tasks[4].id},
        )

        # Assert - Should detect cycle
        assert_status_code(response, 422)
        assert "cycle" in response.json()["detail"].lower()

    async def test_diamond_dependency_pattern(
        self, client: AsyncClient, task_factory, task_dependency_factory
    ):
        """Test diamond pattern (A -> B, A -> C, B -> D, C -> D) - no cycle."""
        # Arrange
        task_a = await task_factory(name="タスクA")
        task_b = await task_factory(name="タスクB")
        task_c = await task_factory(name="タスクC")
        task_d = await task_factory(name="タスクD")

        # Create diamond: A -> B -> D and A -> C -> D
        await task_dependency_factory(task_id=task_b.id, depends_on_task_id=task_a.id)
        await task_dependency_factory(task_id=task_c.id, depends_on_task_id=task_a.id)
        await task_dependency_factory(task_id=task_d.id, depends_on_task_id=task_b.id)

        # Act - Add D depending on C (completing the diamond)
        response = await client.post(
            f"/api/v1/tasks/{task_d.id}/dependencies",
            json={"depends_on_task_id": task_c.id},
        )

        # Assert - Should succeed (diamond is not a cycle)
        assert_status_code(response, 201)

        # Verify D has both B and C as dependencies
        response = await client.get(f"/api/v1/tasks/{task_d.id}/dependencies")
        data = response.json()
        dep_ids = [d["id"] for d in data["depends_on"]]
        assert task_b.id in dep_ids
        assert task_c.id in dep_ids
