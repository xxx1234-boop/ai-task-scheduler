from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models import TimeEntry, TimeEntryUpdate
from app.services.base import BaseCRUDService
from app.schemas.common import PaginatedResponse, TimeEntryCreate
from app.schemas.responses import TimeEntryResponse
from app.dependencies import CommonQueryParams

router = APIRouter()
service = BaseCRUDService[TimeEntry, TimeEntryUpdate](TimeEntry)


@router.get("", response_model=PaginatedResponse[TimeEntryResponse])
async def list_time_entries(
    commons: CommonQueryParams = Depends(),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    session: AsyncSession = Depends(get_session),
):
    """Get all time entries with filtering and pagination."""
    filters = {}
    if task_id is not None:
        filters["task_id"] = task_id

    items, total = await service.get_all(
        session,
        skip=commons.skip,
        limit=commons.limit,
        filters=filters,
        order_by=commons.sort or "-start_time",
    )

    return PaginatedResponse(
        items=items, total=total, skip=commons.skip, limit=commons.limit
    )


@router.get("/{id}", response_model=TimeEntryResponse)
async def get_time_entry(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single time entry by ID."""
    return await service.get_by_id(session, id)


@router.post(
    "", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED
)
async def create_time_entry(
    time_entry_in: TimeEntryCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new time entry."""
    time_entry = TimeEntry(**time_entry_in.model_dump())
    return await service.create(session, time_entry)


@router.patch("/{id}", response_model=TimeEntryResponse)
async def update_time_entry(
    id: int,
    time_entry_update: TimeEntryUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a time entry (partial update)."""
    return await service.update(session, id, time_entry_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a time entry."""
    await service.delete(session, id)
