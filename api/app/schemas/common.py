from typing import Generic, TypeVar, List

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: List[T]
    total: int
    skip: int = 0
    limit: int = 50


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict

    @classmethod
    def create(cls, code: str, message: str, details: dict = None):
        """Create error response with standard format."""
        return cls(
            error={"code": code, "message": message, "details": details or {}}
        )
