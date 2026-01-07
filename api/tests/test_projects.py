"""
Tests for Projects CRUD API endpoints.

This file serves as the reference implementation for standard CRUD testing patterns.
Other resource tests (genres, schedules, time_entries) follow similar patterns.

Endpoints tested:
- POST /api/v1/projects - Create project
- GET /api/v1/projects - List projects with pagination/sorting
- GET /api/v1/projects/{id} - Get single project
- PATCH /api/v1/projects/{id} - Update project
- DELETE /api/v1/projects/{id} - Delete project
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Project
from tests.utils import (
    assert_pagination_structure,
    assert_partial_match,
    assert_sorted_by,
    assert_status_code,
    assert_validation_error,
    count_records,
    record_exists,
)


class TestProjectCRUD:
    """Test standard CRUD operations for projects."""

    async def test_create_project_success(self, client: AsyncClient):
        """Test creating a new project with all required fields."""
        # Arrange
        project_data = {
            "name": "Research on AI",
            "description": "Machine learning research project",
            "is_active": True,
        }

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()

        assert data["name"] == "Research on AI"
        assert data["description"] == "Machine learning research project"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_project_with_deadline(
        self, client: AsyncClient, project_factory
    ):
        """Test creating a project with optional deadline field."""
        # Arrange - use factory which properly handles datetime
        deadline = datetime.now() + timedelta(days=30)
        project = await project_factory(
            name="Project with Deadline",
            deadline=deadline,
            is_active=True,
        )

        # Act - verify through GET
        response = await client.get(f"/api/v1/projects/{project.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert "deadline" in data
        assert data["deadline"] is not None

    async def test_create_project_missing_name(self, client: AsyncClient):
        """Test that creating a project without required name field fails."""
        # Arrange
        project_data = {"description": "No name provided"}

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        assert_validation_error(response)

    async def test_list_projects_empty(self, client: AsyncClient):
        """Test listing projects when database is empty."""
        # Act
        response = await client.get("/api/v1/projects")

        # Assert
        assert_pagination_structure(response, expected_total=0)
        data = response.json()
        assert data["items"] == []

    async def test_list_projects_with_single_project(
        self, client: AsyncClient, project_factory
    ):
        """Test listing projects with one project in database."""
        # Arrange
        project = await project_factory(name="Single Project")

        # Act
        response = await client.get("/api/v1/projects")

        # Assert
        assert_pagination_structure(response, expected_total=1)
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == project.id
        assert data["items"][0]["name"] == "Single Project"

    async def test_list_projects_with_pagination(
        self, client: AsyncClient, project_factory
    ):
        """Test pagination with skip and limit parameters."""
        # Arrange: Create 15 projects
        for i in range(15):
            await project_factory(name=f"Project {i:02d}")

        # Act: Get first page (10 items)
        response = await client.get("/api/v1/projects?skip=0&limit=10")

        # Assert
        assert_pagination_structure(response)
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["skip"] == 0
        assert data["limit"] == 10

        # Act: Get second page (5 remaining items)
        response = await client.get("/api/v1/projects?skip=10&limit=10")

        # Assert
        assert_pagination_structure(response)
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["skip"] == 10

    async def test_list_projects_pagination_beyond_total(
        self, client: AsyncClient, project_factory
    ):
        """Test pagination when skip exceeds total records."""
        # Arrange
        await project_factory(name="Only Project")

        # Act
        response = await client.get("/api/v1/projects?skip=100&limit=10")

        # Assert
        assert_pagination_structure(response, expected_total=1)
        data = response.json()
        assert len(data["items"]) == 0

    async def test_get_project_by_id(self, client: AsyncClient, project_factory):
        """Test getting a single project by ID."""
        # Arrange
        project = await project_factory(
            name="Test Project", description="Test Description"
        )

        # Act
        response = await client.get(f"/api/v1/projects/{project.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["id"] == project.id
        assert data["name"] == "Test Project"
        assert data["description"] == "Test Description"

    async def test_get_project_not_found(self, client: AsyncClient):
        """Test getting non-existent project returns 404."""
        # Act
        response = await client.get("/api/v1/projects/99999")

        # Assert
        assert_status_code(response, 404)

    async def test_update_project_partial(
        self, client: AsyncClient, project_factory
    ):
        """Test partial update of project fields."""
        # Arrange
        project = await project_factory(
            name="Original Name",
            description="Original Description",
            is_active=True,
        )

        # Act: Update only name
        update_data = {"name": "Updated Name"}
        response = await client.patch(
            f"/api/v1/projects/{project.id}", json=update_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Original Description"  # Unchanged
        assert data["is_active"] is True  # Unchanged

    async def test_update_project_multiple_fields(
        self, client: AsyncClient, project_factory
    ):
        """Test updating multiple fields at once."""
        # Arrange
        project = await project_factory(
            name="Old Name", description="Old Description", is_active=True
        )

        # Act
        update_data = {
            "name": "New Name",
            "description": "New Description",
            "is_active": False,
        }
        response = await client.patch(
            f"/api/v1/projects/{project.id}", json=update_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert_partial_match(update_data, data)

    async def test_update_project_not_found(self, client: AsyncClient):
        """Test updating non-existent project returns 404."""
        # Act
        update_data = {"name": "New Name"}
        response = await client.patch("/api/v1/projects/99999", json=update_data)

        # Assert
        assert_status_code(response, 404)

    async def test_delete_project(
        self, client: AsyncClient, project_factory, test_session: AsyncSession
    ):
        """Test deleting a project."""
        # Arrange
        project = await project_factory(name="To Delete")
        project_id = project.id

        # Act
        response = await client.delete(f"/api/v1/projects/{project_id}")

        # Assert
        assert_status_code(response, 204)

        # Verify project is actually deleted from database
        exists = await record_exists(test_session, Project, project_id)
        assert not exists, "Project should be deleted from database"

        # Verify GET returns 404
        get_response = await client.get(f"/api/v1/projects/{project_id}")
        assert_status_code(get_response, 404)

    async def test_delete_project_not_found(self, client: AsyncClient):
        """Test deleting non-existent project returns 404."""
        # Act
        response = await client.delete("/api/v1/projects/99999")

        # Assert
        assert_status_code(response, 404)


class TestProjectSorting:
    """Test sorting functionality for project listings."""

    async def test_sort_by_name_ascending(
        self, client: AsyncClient, project_factory
    ):
        """Test sorting projects by name in ascending order."""
        # Arrange
        await project_factory(name="Zebra Project")
        await project_factory(name="Alpha Project")
        await project_factory(name="Beta Project")

        # Act
        response = await client.get("/api/v1/projects?sort=name")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert_sorted_by(data["items"], "name", descending=False)

    async def test_sort_by_name_descending(
        self, client: AsyncClient, project_factory
    ):
        """Test sorting projects by name in descending order."""
        # Arrange
        await project_factory(name="Alpha Project")
        await project_factory(name="Beta Project")
        await project_factory(name="Gamma Project")

        # Act
        response = await client.get("/api/v1/projects?sort=-name")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert_sorted_by(data["items"], "name", descending=True)

    async def test_sort_by_created_at_descending(
        self, client: AsyncClient, project_factory
    ):
        """Test sorting projects by created_at (most recent first)."""
        # Arrange
        project1 = await project_factory(name="First")
        project2 = await project_factory(name="Second")
        project3 = await project_factory(name="Third")

        # Act
        response = await client.get("/api/v1/projects?sort=-created_at")

        # Assert
        assert_status_code(response, 200)
        data = response.json()

        # Most recent first
        ids = [item["id"] for item in data["items"]]
        assert ids == [project3.id, project2.id, project1.id]


class TestProjectValidation:
    """Test validation error handling."""

    async def test_create_with_invalid_field_type(self, client: AsyncClient):
        """Test creating project with wrong field type."""
        # Arrange
        project_data = {
            "name": "Valid Name",
            "is_active": "not a boolean",  # Should be boolean
        }

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        assert_validation_error(response)

    async def test_create_with_extra_unknown_field(self, client: AsyncClient):
        """Test that extra unknown fields are ignored or rejected."""
        # Arrange
        project_data = {
            "name": "Project Name",
            "unknown_field": "should be ignored",
        }

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        # FastAPI with Pydantic ignores extra fields by default
        assert_status_code(response, 201)
        data = response.json()
        assert "unknown_field" not in data


class TestProjectEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_create_project_with_very_long_name(self, client: AsyncClient):
        """Test creating project with maximum length name."""
        # Arrange: Max length is 200 characters
        long_name = "A" * 200
        project_data = {"name": long_name}

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["name"] == long_name

    async def test_create_project_with_empty_description(
        self, client: AsyncClient
    ):
        """Test creating project with empty description."""
        # Arrange
        project_data = {"name": "Project", "description": ""}

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["description"] == ""

    async def test_create_project_with_null_description(
        self, client: AsyncClient
    ):
        """Test creating project with null description."""
        # Arrange
        project_data = {"name": "Project", "description": None}

        # Act
        response = await client.post("/api/v1/projects", json=project_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["description"] is None
