from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.services.dashboard_service import dashboard_service
from app.schemas.dashboard import (
    KanbanResponse,
    TodayResponse,
    TimelineResponse,
    WeeklyResponse,
    StatsResponse,
    SummaryResponse,
)

router = APIRouter()


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    session: AsyncSession = Depends(get_session),
):
    """Get overall summary for dashboard header.

    Returns today's progress, this week's progress, urgent tasks count, and timer status.
    """
    return await dashboard_service.get_summary(session)


@router.get("/today", response_model=TodayResponse)
async def get_today(
    session: AsyncSession = Depends(get_session),
):
    """Get today's schedule and summary.

    Returns today's scheduled tasks, actual hours worked, and timer status.
    """
    return await dashboard_service.get_today(session)


@router.get("/kanban", response_model=KanbanResponse)
async def get_kanban(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    session: AsyncSession = Depends(get_session),
):
    """Get kanban board data.

    Returns tasks grouped by status (todo, doing, waiting, done) with blocking info.
    """
    return await dashboard_service.get_kanban(session, project_id=project_id)


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    target_date: Optional[date] = Query(None, description="Target date (default: today)"),
    session: AsyncSession = Depends(get_session),
):
    """Get timeline data for a specific date.

    Returns planned (schedules) and actual (time entries) time blocks.
    """
    return await dashboard_service.get_timeline(session, target_date=target_date)


@router.get("/weekly", response_model=WeeklyResponse)
async def get_weekly(
    week_start: Optional[date] = Query(None, description="Week start date (default: this Monday)"),
    session: AsyncSession = Depends(get_session),
):
    """Get weekly summary.

    Returns daily planned/actual hours and totals by project/genre.
    """
    return await dashboard_service.get_weekly(session, week_start=week_start)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    period: str = Query("week", description="Period: week, month, or quarter"),
    session: AsyncSession = Depends(get_session),
):
    """Get statistics for the specified period.

    Returns estimation accuracy, time distribution, completion rate, and context switches.
    """
    return await dashboard_service.get_stats(session, period=period)
