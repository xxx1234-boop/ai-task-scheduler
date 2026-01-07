from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.services.timer_service import TimerService
from app.schemas.workflow_requests import TimerStartRequest, TimerStopRequest
from app.schemas.workflow_responses import (
    TimerStartResponse,
    TimerStopResponse,
    TimerStatusResponse,
    PreviousTimerInfo,
)

router = APIRouter()
service = TimerService()


@router.post("/start", response_model=TimerStartResponse, status_code=status.HTTP_200_OK)
async def start_timer(
    request: TimerStartRequest,
    session: AsyncSession = Depends(get_session),
):
    """Start timer for a task (auto-stops running timer if exists).

    Args:
        request: Timer start request with task_id or task_name
        session: Database session

    Returns:
        TimerStartResponse with new timer info and previous timer if auto-stopped
    """
    entry, previous = await service.start_timer(
        session, task_id=request.task_id, task_name=request.task_name
    )

    # Load task relationship
    await session.refresh(entry, ["task"])

    # Load project if available
    project_name = None
    if entry.task.project_id:
        await session.refresh(entry.task, ["project"])
        project_name = entry.task.project.name if entry.task.project else None

    # Build previous entry info if exists
    previous_entry_info = None
    if previous:
        await session.refresh(previous, ["task"])
        previous_entry_info = PreviousTimerInfo(
            time_entry_id=previous.id,
            task_name=previous.task.name,
            duration_minutes=previous.duration_minutes or 0,
            stopped_at=previous.end_time,
        )

    return TimerStartResponse(
        time_entry_id=entry.id,
        task_id=entry.task_id,
        task_name=entry.task.name,
        project_name=project_name,
        start_time=entry.start_time,
        previous_entry=previous_entry_info,
    )


@router.post("/stop", response_model=TimerStopResponse, status_code=status.HTTP_200_OK)
async def stop_timer(
    request: TimerStopRequest,
    session: AsyncSession = Depends(get_session),
):
    """Stop the currently running timer.

    Args:
        request: Timer stop request with optional note
        session: Database session

    Returns:
        TimerStopResponse with stopped timer info
    """
    entry = await service.stop_timer(session, note=request.note)

    # Load task relationship
    await session.refresh(entry, ["task"])

    return TimerStopResponse(
        time_entry_id=entry.id,
        task_id=entry.task_id,
        task_name=entry.task.name,
        start_time=entry.start_time,
        end_time=entry.end_time,
        duration_minutes=entry.duration_minutes,
        task_actual_hours_total=entry.task.actual_hours,
    )


@router.get("/status", response_model=TimerStatusResponse, status_code=status.HTTP_200_OK)
async def get_timer_status(session: AsyncSession = Depends(get_session)):
    """Get current timer status.

    Args:
        session: Database session

    Returns:
        TimerStatusResponse with current timer status
    """
    status_data = await service.get_timer_status(session)
    return TimerStatusResponse(**status_data)
