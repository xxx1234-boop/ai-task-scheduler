from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models import Schedule, ScheduleUpdate
from app.services.base import BaseCRUDService
from app.schemas.common import PaginatedResponse
from app.schemas.responses import ScheduleResponse
from app.dependencies import CommonQueryParams

router = APIRouter()
service = BaseCRUDService[Schedule, ScheduleUpdate](Schedule)


@router.get("", response_model=PaginatedResponse[ScheduleResponse])
async def list_schedules(
    commons: CommonQueryParams = Depends(),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    date_from: Optional[datetime] = Query(
        None, description="Filter schedules from this date"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter schedules until this date"
    ),
    session: AsyncSession = Depends(get_session),
):
    """Get all schedules with filtering and pagination."""
    filters = {}
    if task_id is not None:
        filters["task_id"] = task_id

    items, total = await service.get_all(
        session,
        skip=commons.skip,
        limit=commons.limit,
        filters=filters,
        order_by=commons.sort or "-scheduled_date",
    )

    # TODO: Add date range filtering (requires custom service method)
    # For now, basic task_id filtering works via base service

    return PaginatedResponse(
        items=items, total=total, skip=commons.skip, limit=commons.limit
    )


@router.get("/{id}", response_model=ScheduleResponse)
async def get_schedule(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single schedule by ID."""
    return await service.get_by_id(session, id)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule: Schedule,
    session: AsyncSession = Depends(get_session),
):
    """Create a new schedule."""
    return await service.create(session, schedule)


@router.patch("/{id}", response_model=ScheduleResponse)
async def update_schedule(
    id: int,
    schedule_update: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a schedule (partial update)."""
    return await service.update(session, id, schedule_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a schedule."""
    await service.delete(session, id)
