"""Workflow API endpoints for schedule generation."""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.services.schedule_service import ScheduleService
from app.schemas.workflow_requests import GenerateWeeklyScheduleRequest
from app.schemas.workflow_responses import WeeklyScheduleResponse
from app.clients.claude_client import ClaudeAPIException
from app.exceptions import ValidationException

router = APIRouter()


@router.post(
    "/generate-weekly",
    response_model=WeeklyScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="週次スケジュール自動生成",
    description="Claude APIを使用して、タスクの優先度・締切・依存関係を考慮した最適な週間スケジュールを生成します。",
)
async def generate_weekly_schedule(
    request: GenerateWeeklyScheduleRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate optimized weekly schedule using Claude API.

    This endpoint:
    1. Gathers all active tasks (todo, doing, waiting) with remaining hours
    2. Collects task dependencies
    3. Calls Claude API for schedule optimization
    4. Creates schedule records in the database
    5. Returns the generated schedule with summary and warnings

    Args:
        request: Schedule generation request with week_start, preferences, and fixed_events

    Returns:
        WeeklyScheduleResponse with schedules, summary, and warnings
    """
    service = ScheduleService()

    try:
        return await service.generate_weekly_schedule(
            session=session,
            week_start=request.week_start,
            preferences=request.preferences,
            fixed_events=request.fixed_events,
            clear_existing=request.clear_existing,
        )
    except ClaudeAPIException as e:
        if e.status_code == 503:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Claude API key is not configured. Please set ANTHROPIC_API_KEY.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {e.message}",
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
