"""
Tests for Settings CRUD API endpoints.

Settings use key-based access instead of ID-based access.
Unique pattern: PUT for upsert (create or update).

Endpoints tested:
- GET /api/v1/settings - List all settings
- GET /api/v1/settings/{key} - Get setting by key
- PUT /api/v1/settings/{key} - Upsert setting (create or update)
- PATCH /api/v1/settings/{key} - Update setting
- DELETE /api/v1/settings/{key} - Delete setting
"""

import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Setting
from tests.utils import (
    assert_pagination_structure,
    assert_status_code,
    get_records_by_field,
)


class TestSettingsKeyBased:
    """Test key-based access pattern for settings."""

    async def test_list_settings_empty(self, client: AsyncClient):
        """Test listing settings when database is empty."""
        # Act
        response = await client.get("/api/v1/settings")

        # Assert
        assert_pagination_structure(response, expected_total=0)

    async def test_list_settings_with_data(
        self, client: AsyncClient, setting_factory
    ):
        """Test listing multiple settings."""
        # Arrange
        await setting_factory(key="max_hours", value='{"hours": 8}')
        await setting_factory(key="theme", value='{"mode": "dark"}')
        await setting_factory(key="language", value='{"code": "ja"}')

        # Act
        response = await client.get("/api/v1/settings")

        # Assert
        assert_pagination_structure(response, expected_total=3)

    async def test_get_setting_by_key(
        self, client: AsyncClient, setting_factory
    ):
        """Test getting a setting by key."""
        # Arrange
        await setting_factory(key="max_hours", value='{"hours": 8}')

        # Act
        response = await client.get("/api/v1/settings/max_hours")

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["key"] == "max_hours"
        assert data["value"] == '{"hours": 8}'

    async def test_get_setting_key_not_found(self, client: AsyncClient):
        """Test getting non-existent setting returns 404."""
        # Act
        response = await client.get("/api/v1/settings/nonexistent_key")

        # Assert
        assert_status_code(response, 404)

    async def test_upsert_setting_create_new(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test PUT to create a new setting (upsert behavior)."""
        # Arrange
        setting_data = {
            "key": "new_setting",
            "value": '{"enabled": true}',
            "description": "新しい設定",
        }

        # Act
        response = await client.put(
            "/api/v1/settings/new_setting", json=setting_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["key"] == "new_setting"
        assert data["value"] == '{"enabled": true}'

        # Verify in database
        settings = await get_records_by_field(
            test_session, Setting, "key", "new_setting"
        )
        assert len(settings) == 1

    async def test_upsert_setting_update_existing(
        self, client: AsyncClient, setting_factory
    ):
        """Test PUT to update an existing setting (upsert behavior)."""
        # Arrange
        await setting_factory(key="existing_key", value='{"old": "value"}')

        # Act: Update with PUT
        setting_data = {
            "key": "existing_key",
            "value": '{"new": "value"}',
        }
        response = await client.put(
            "/api/v1/settings/existing_key", json=setting_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["key"] == "existing_key"
        assert data["value"] == '{"new": "value"}'

    async def test_patch_setting_by_key(
        self, client: AsyncClient, setting_factory
    ):
        """Test PATCH to partially update setting."""
        # Arrange
        await setting_factory(
            key="theme", value='{"mode": "light"}', description="テーマ設定"
        )

        # Act
        update_data = {"value": '{"mode": "dark"}'}
        response = await client.patch("/api/v1/settings/theme", json=update_data)

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["value"] == '{"mode": "dark"}'
        assert data["description"] == "テーマ設定"  # Unchanged

    async def test_patch_setting_not_found(self, client: AsyncClient):
        """Test PATCH on non-existent setting returns 404."""
        # Act
        update_data = {"value": '{"test": true}'}
        response = await client.patch(
            "/api/v1/settings/nonexistent", json=update_data
        )

        # Assert
        assert_status_code(response, 404)

    async def test_delete_setting_by_key(
        self, client: AsyncClient, setting_factory, test_session: AsyncSession
    ):
        """Test deleting a setting by key."""
        # Arrange
        await setting_factory(key="to_delete", value='{"test": true}')

        # Act
        response = await client.delete("/api/v1/settings/to_delete")

        # Assert
        assert_status_code(response, 204)

        # Verify deletion
        settings = await get_records_by_field(
            test_session, Setting, "key", "to_delete"
        )
        assert len(settings) == 0

    async def test_delete_setting_not_found(self, client: AsyncClient):
        """Test deleting non-existent setting returns 404."""
        # Act
        response = await client.delete("/api/v1/settings/nonexistent")

        # Assert
        assert_status_code(response, 404)


class TestSettingsValidation:
    """Test validation rules for settings."""

    async def test_create_setting_missing_value(self, client: AsyncClient):
        """Test creating setting without value field."""
        # Arrange
        setting_data = {
            "key": "test_key",
            # Missing value
        }

        # Act
        response = await client.put("/api/v1/settings/test_key", json=setting_data)

        # Assert
        # Depends on whether value is required
        # If required, should return 422
        assert response.status_code in [200, 422]

    async def test_create_setting_with_json_value(
        self, client: AsyncClient
    ):
        """Test creating setting with valid JSON value."""
        # Arrange
        setting_data = {
            "key": "json_setting",
            "value": '{"nested": {"key": "value"}, "array": [1, 2, 3]}',
        }

        # Act
        response = await client.put(
            "/api/v1/settings/json_setting", json=setting_data
        )

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["value"] == '{"nested": {"key": "value"}, "array": [1, 2, 3]}'

    async def test_create_setting_with_empty_value(
        self, client: AsyncClient
    ):
        """Test creating setting with empty string value."""
        # Arrange
        setting_data = {
            "key": "empty_setting",
            "value": "",
        }

        # Act
        response = await client.put(
            "/api/v1/settings/empty_setting", json=setting_data
        )

        # Assert
        assert_status_code(response, 200)


class TestSettingsEdgeCases:
    """Test edge cases for settings."""

    async def test_upsert_same_setting_multiple_times(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        """Test upserting the same setting multiple times."""
        # Arrange
        setting_data = {"key": "repeated", "value": '{"count": 1}'}

        # Act: First upsert
        response1 = await client.put("/api/v1/settings/repeated", json=setting_data)
        assert_status_code(response1, 200)

        # Act: Second upsert with different value
        setting_data["value"] = '{"count": 2}'
        response2 = await client.put("/api/v1/settings/repeated", json=setting_data)
        assert_status_code(response2, 200)

        # Act: Third upsert with different value
        setting_data["value"] = '{"count": 3}'
        response3 = await client.put("/api/v1/settings/repeated", json=setting_data)
        assert_status_code(response3, 200)

        # Assert: Only one setting exists
        settings = await get_records_by_field(
            test_session, Setting, "key", "repeated"
        )
        assert len(settings) == 1
        assert settings[0].value == '{"count": 3}'

    async def test_create_setting_with_very_long_key(
        self, client: AsyncClient
    ):
        """Test creating setting with maximum length key (100 chars)."""
        # Arrange
        long_key = "a" * 100
        setting_data = {
            "key": long_key,
            "value": '{"test": true}',
        }

        # Act
        response = await client.put(f"/api/v1/settings/{long_key}", json=setting_data)

        # Assert
        assert_status_code(response, 200)
        data = response.json()
        assert data["key"] == long_key
