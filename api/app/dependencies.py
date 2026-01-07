from typing import Optional

from fastapi import Query


class CommonQueryParams:
    """Common query parameters for list endpoints."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
        sort: Optional[str] = Query(
            None, description="Field to sort by (prefix with - for descending)"
        ),
    ):
        self.skip = skip
        self.limit = limit
        self.sort = sort
