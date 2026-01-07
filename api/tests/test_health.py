"""
Tests for health check endpoint.

This is the simplest test file to verify the test infrastructure is working correctly:
- Testcontainers PostgreSQL setup
- Database migrations applied
- FastAPI test client working
- Database connectivity
"""

import pytest
from httpx import AsyncClient

from tests.utils import assert_status_code


class TestHealthCheck:
    """Test health check endpoint."""

    async def test_health_check_returns_200(self, client: AsyncClient):
        """Test that health check endpoint returns 200 status."""
        # Act
        response = await client.get("/health")

        # Assert
        assert_status_code(response, 200)

    async def test_health_check_returns_healthy_status(self, client: AsyncClient):
        """Test that health check returns healthy status with database connection."""
        # Act
        response = await client.get("/health")

        # Assert
        assert_status_code(response, 200)
        data = response.json()

        # Check response structure
        assert "status" in data, "Response missing 'status' field"
        assert "database" in data, "Response missing 'database' field"

        # Check values
        assert data["status"] == "healthy", "Expected healthy status"
        assert data["database"] == "connected", "Expected database to be connected"

    async def test_health_check_no_error_field(self, client: AsyncClient):
        """Test that healthy response does not contain error field."""
        # Act
        response = await client.get("/health")

        # Assert
        assert_status_code(response, 200)
        data = response.json()

        # Should not have error field when healthy
        assert "error" not in data, "Healthy response should not contain error field"
