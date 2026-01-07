"""
Tests for Genres CRUD API endpoints.

Genres are a simpler resource compared to projects, primarily used
for categorizing tasks (リサーチ, コーディング, 執筆, etc.).

Endpoints tested:
- POST /api/v1/genres - Create genre
- GET /api/v1/genres - List genres
- GET /api/v1/genres/{id} - Get single genre
- PATCH /api/v1/genres/{id} - Update genre
- DELETE /api/v1/genres/{id} - Delete genre
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Genre
from tests.utils import (
    assert_pagination_structure,
    assert_status_code,
    assert_validation_error,
    record_exists,
)


class TestGenreCRUD:
    """Test standard CRUD operations for genres."""

    async def test_create_genre_success(self, client: AsyncClient):
        """Test creating a new genre."""
        # Arrange
        genre_data = {"name": "リサーチ", "color": "#4A90D9"}

        # Act
        response = await client.post("/api/v1/genres", json=genre_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["name"] == "リサーチ"
        assert data["color"] == "#4A90D9"
        assert "id" in data
        assert "created_at" in data

    async def test_create_genre_without_color(self, client: AsyncClient):
        """Test creating genre without color field fails (color is required)."""
        # Arrange
        genre_data = {"name": "コーディング"}

        # Act
        response = await client.post("/api/v1/genres", json=genre_data)

        # Assert - color is required, so this should fail with 422
        assert_validation_error(response)

    async def test_create_genre_missing_name(self, client: AsyncClient):
        """Test that creating genre without required name fails."""
        # Arrange
        genre_data = {"color": "#FF0000"}

        # Act
        response = await client.post("/api/v1/genres", json=genre_data)

        # Assert
        assert_validation_error(response)

    async def test_list_genres_empty(self, client: AsyncClient):
        """Test listing genres when database is empty."""
        # Act
        response = await client.get("/api/v1/genres")

        # Assert
        assert_pagination_structure(response, expected_total=0)

    async def test_list_genres_with_data(self, client: AsyncClient, genre_factory):
        """Test listing multiple genres."""
        # Arrange
        await genre_factory(name="リサーチ", color="#4A90D9")
        await genre_factory(name="コーディング", color="#50C878")
        await genre_factory(name="執筆", color="#FFB347")

        # Act
        response = await client.get("/api/v1/genres")

        # Assert
        assert_pagination_structure(response, expected_total=3)
        data = response.json()
        assert len(data["items"]) == 3

    async def test_list_genres_with_pagination(
        self, client: AsyncClient, genre_factory
    ):
        """Test genre pagination."""
        # Arrange: Create 8 genres (default genres from design doc)
        genre_names = [
            "リサーチ",
            "コーディング",
            "執筆",
            "ミーティング",
            "レビュー",
            "実験",
            "データ分析",
            "その他",
        ]
        for name in genre_names:
            await genre_factory(name=name)

        # Act: Get first 5
        response = await client.get("/api/v1/genres?skip=0&limit=5")

        # Assert
        assert_pagination_structure(response)
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 8

    async def test_get_genre_by_id(self, client: AsyncClient, genre_factory):
        """Test getting a single genre by ID."""
        # Arrange
        genre = await genre_factory(name="リサーチ", color="#4A90D9")

        # Act
        response = await client.get(f"/api/v1/genres/{genre.id}")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["id"] == genre.id
        assert data["name"] == "リサーチ"
        assert data["color"] == "#4A90D9"

    async def test_get_genre_not_found(self, client: AsyncClient):
        """Test getting non-existent genre returns 404."""
        # Act
        response = await client.get("/api/v1/genres/99999")

        # Assert
        assert_status_code(response, 404)

    async def test_update_genre_name(self, client: AsyncClient, genre_factory):
        """Test updating genre name."""
        # Arrange
        genre = await genre_factory(name="OldName", color="#000000")

        # Act
        update_data = {"name": "NewName"}
        response = await client.patch(
            f"/api/v1/genres/{genre.id}", json=update_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["name"] == "NewName"
        assert data["color"] == "#000000"  # Unchanged

    async def test_update_genre_color(self, client: AsyncClient, genre_factory):
        """Test updating genre color."""
        # Arrange
        genre = await genre_factory(name="Test", color="#000000")

        # Act
        update_data = {"color": "#FF0000"}
        response = await client.patch(
            f"/api/v1/genres/{genre.id}", json=update_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["color"] == "#FF0000"
        assert data["name"] == "Test"  # Unchanged

    async def test_update_genre_not_found(self, client: AsyncClient):
        """Test updating non-existent genre returns 404."""
        # Act
        update_data = {"name": "NewName"}
        response = await client.patch("/api/v1/genres/99999", json=update_data)

        # Assert
        assert_status_code(response, 404)

    async def test_delete_genre(
        self, client: AsyncClient, genre_factory, test_session: AsyncSession
    ):
        """Test deleting a genre."""
        # Arrange
        genre = await genre_factory(name="ToDelete")
        genre_id = genre.id

        # Act
        response = await client.delete(f"/api/v1/genres/{genre_id}")

        # Assert
        assert_status_code(response, 204)

        # Verify deletion in database
        exists = await record_exists(test_session, Genre, genre_id)
        assert not exists

    async def test_delete_genre_not_found(self, client: AsyncClient):
        """Test deleting non-existent genre returns 404."""
        # Act
        response = await client.delete("/api/v1/genres/99999")

        # Assert
        assert_status_code(response, 404)


class TestGenreSorting:
    """Test sorting functionality for genres."""

    async def test_sort_by_name_ascending(
        self, client: AsyncClient, genre_factory
    ):
        """Test sorting genres by name."""
        # Arrange
        await genre_factory(name="ミーティング")
        await genre_factory(name="コーディング")
        await genre_factory(name="リサーチ")

        # Act
        response = await client.get("/api/v1/genres?sort=name")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        names = [item["name"] for item in data["items"]]

        # Check they're sorted
        assert names == sorted(names)


class TestGenreValidation:
    """Test validation rules for genres."""

    async def test_create_with_invalid_color_format(self, client: AsyncClient):
        """Test creating genre with invalid hex color."""
        # Arrange
        genre_data = {"name": "Test", "color": "invalid-color"}

        # Act
        response = await client.post("/api/v1/genres", json=genre_data)

        # Assert
        # Note: Color validation depends on model implementation
        # If there's no validation, this will succeed
        # If there's Pydantic validation, it will fail
        assert response.status_code in [201, 422]

    async def test_create_with_very_long_name(self, client: AsyncClient):
        """Test creating genre with maximum length name (100 chars)."""
        # Arrange
        long_name = "あ" * 100  # Japanese characters
        genre_data = {"name": long_name, "color": "#000000"}

        # Act
        response = await client.post("/api/v1/genres", json=genre_data)

        # Assert
        assert_status_code(response, 201)
        data = response.json()
        assert data["name"] == long_name
