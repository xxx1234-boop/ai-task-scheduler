"""
Test utility functions and assertions.

This module provides helper functions for common testing patterns:
- Response assertions (status codes, error messages, pagination)
- Database query helpers (counting, existence checks)
- Data comparison utilities
"""

from typing import Any, Optional, Type

from httpx import Response
from sqlalchemy import func, select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


# =============================================================================
# Response assertion helpers
# =============================================================================


def assert_status_code(response: Response, expected: int):
    """
    Assert that the response has the expected status code.

    Args:
        response: The HTTP response
        expected: Expected status code

    Raises:
        AssertionError: If status code doesn't match
    """
    assert response.status_code == expected, (
        f"Expected status code {expected}, got {response.status_code}. "
        f"Response body: {response.text}"
    )


def assert_error_code(response: Response, code: str):
    """
    Assert that the response contains a specific error code.

    Args:
        response: The HTTP response
        code: Expected error code

    Raises:
        AssertionError: If error code doesn't match
    """
    data = response.json()
    assert "error" in data, "Response does not contain 'error' field"
    assert data["error"].get("code") == code, (
        f"Expected error code '{code}', got '{data['error'].get('code')}'"
    )


def assert_pagination_structure(
    response: Response, expected_total: Optional[int] = None
):
    """
    Assert that the response has proper pagination structure.

    Args:
        response: The HTTP response
        expected_total: Optional expected total count

    Raises:
        AssertionError: If pagination structure is invalid
    """
    assert_status_code(response, 200)
    data = response.json()

    # Check pagination fields exist
    assert "items" in data, "Response missing 'items' field"
    assert "total" in data, "Response missing 'total' field"
    assert "skip" in data, "Response missing 'skip' field"
    assert "limit" in data, "Response missing 'limit' field"

    # Check types
    assert isinstance(data["items"], list), "'items' should be a list"
    assert isinstance(data["total"], int), "'total' should be an integer"
    assert isinstance(data["skip"], int), "'skip' should be an integer"
    assert isinstance(data["limit"], int), "'limit' should be an integer"

    # Check optional expected total
    if expected_total is not None:
        assert data["total"] == expected_total, (
            f"Expected total={expected_total}, got {data['total']}"
        )


def assert_validation_error(response: Response):
    """
    Assert that the response is a 422 validation error.

    Args:
        response: The HTTP response

    Raises:
        AssertionError: If not a validation error
    """
    assert_status_code(response, 422)
    data = response.json()
    assert "error" in data, "Response does not contain 'error' field"
    assert data["error"].get("code") == "VALIDATION_ERROR", (
        "Error code should be VALIDATION_ERROR"
    )


# =============================================================================
# Database query helpers
# =============================================================================


async def count_records(session: AsyncSession, model_class: Type[SQLModel]) -> int:
    """
    Count the number of records for a given model.

    Args:
        session: Database session
        model_class: SQLModel class to count

    Returns:
        Number of records
    """
    result = await session.execute(select(func.count()).select_from(model_class))
    count = result.scalar_one()
    return count


async def get_record_by_id(
    session: AsyncSession, model_class: Type[SQLModel], record_id: int
) -> Optional[SQLModel]:
    """
    Get a record by its ID.

    Args:
        session: Database session
        model_class: SQLModel class
        record_id: ID of the record

    Returns:
        The record if found, None otherwise
    """
    result = await session.execute(
        select(model_class).where(model_class.id == record_id)
    )
    return result.scalar_one_or_none()


async def record_exists(
    session: AsyncSession, model_class: Type[SQLModel], record_id: int
) -> bool:
    """
    Check if a record exists by its ID.

    Args:
        session: Database session
        model_class: SQLModel class
        record_id: ID of the record

    Returns:
        True if record exists, False otherwise
    """
    record = await get_record_by_id(session, model_class, record_id)
    return record is not None


async def get_records_by_field(
    session: AsyncSession,
    model_class: Type[SQLModel],
    field_name: str,
    field_value: Any,
) -> list[SQLModel]:
    """
    Get all records where a field matches a value.

    Args:
        session: Database session
        model_class: SQLModel class
        field_name: Name of the field to filter by
        field_value: Value to match

    Returns:
        List of matching records
    """
    field = getattr(model_class, field_name)
    result = await session.execute(select(model_class).where(field == field_value))
    return list(result.scalars().all())


# =============================================================================
# Data comparison utilities
# =============================================================================


def assert_model_matches_response(model: SQLModel, response_data: dict):
    """
    Assert that a model instance matches the response data.

    Compares common fields between the model and response.

    Args:
        model: SQLModel instance
        response_data: Dictionary from API response

    Raises:
        AssertionError: If fields don't match
    """
    # Get model fields (excluding relationships)
    model_dict = model.model_dump()

    for key, value in model_dict.items():
        if key in response_data:
            assert response_data[key] == value, (
                f"Field '{key}' mismatch: expected {value}, got {response_data[key]}"
            )


def assert_partial_match(expected: dict, actual: dict):
    """
    Assert that actual dict contains all keys from expected dict with matching values.

    This is useful for partial updates where only some fields are modified.

    Args:
        expected: Dictionary with expected key-value pairs
        actual: Dictionary to check against

    Raises:
        AssertionError: If any expected key is missing or has wrong value
    """
    for key, value in expected.items():
        assert key in actual, f"Expected key '{key}' not found in actual data"
        assert actual[key] == value, (
            f"Key '{key}' mismatch: expected {value}, got {actual[key]}"
        )


def assert_list_contains_ids(items: list[dict], expected_ids: list[int]):
    """
    Assert that a list of items contains all expected IDs.

    Args:
        items: List of dictionaries with 'id' field
        expected_ids: List of expected IDs

    Raises:
        AssertionError: If any expected ID is missing
    """
    actual_ids = {item["id"] for item in items}
    expected_ids_set = set(expected_ids)

    missing = expected_ids_set - actual_ids
    assert not missing, f"Missing IDs: {missing}"


def assert_sorted_by(items: list[dict], field: str, descending: bool = False):
    """
    Assert that a list of items is sorted by a specific field.

    Args:
        items: List of dictionaries
        field: Field name to check sorting
        descending: If True, check descending order

    Raises:
        AssertionError: If list is not properly sorted
    """
    if len(items) < 2:
        return  # Nothing to check

    values = [item[field] for item in items]

    if descending:
        expected = sorted(values, reverse=True)
        assert values == expected, (
            f"Items not sorted by '{field}' (descending). "
            f"Expected order: {expected}, got: {values}"
        )
    else:
        expected = sorted(values)
        assert values == expected, (
            f"Items not sorted by '{field}' (ascending). "
            f"Expected order: {expected}, got: {values}"
        )


# =============================================================================
# Test data helpers
# =============================================================================


def make_create_request(required_fields: dict, **optional_fields) -> dict:
    """
    Create a request body for POST endpoints.

    Args:
        required_fields: Required fields for the request
        **optional_fields: Optional additional fields

    Returns:
        Complete request dictionary
    """
    request = required_fields.copy()
    request.update(optional_fields)
    return request


def make_update_request(**updates) -> dict:
    """
    Create a request body for PATCH endpoints.

    Args:
        **updates: Fields to update

    Returns:
        Update request dictionary
    """
    return updates
