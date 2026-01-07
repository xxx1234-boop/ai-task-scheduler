from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models import Task, TaskCreate, TaskUpdate
from app.services.task_service import TaskService
from app.schemas.common import PaginatedResponse
from app.schemas.responses import TaskResponse
from app.dependencies import CommonQueryParams

router = APIRouter()
service = TaskService(Task)


@router.get("", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    commons: CommonQueryParams = Depends(),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    genre_id: Optional[int] = Query(None, description="Filter by genre ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    has_parent: Optional[bool] = Query(
        None, description="Filter by parent presence (true = has parent, false = no parent)"
    ),
    parent_task_id: Optional[int] = Query(
        None, description="Filter by parent task ID"
    ),
    session: AsyncSession = Depends(get_session),
):
    """Get all tasks with filtering and pagination."""
    items, total = await service.get_all_with_filters(
        session,
        skip=commons.skip,
        limit=commons.limit,
        project_id=project_id,
        genre_id=genre_id,
        status=status,
        priority=priority,
        has_parent=has_parent,
        parent_task_id=parent_task_id,
        sort=commons.sort,
    )

    return PaginatedResponse(
        items=items, total=total, skip=commons.skip, limit=commons.limit
    )


@router.get("/{id}", response_model=TaskResponse)
async def get_task(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single task by ID with relationships loaded."""
    return await service.get_by_id(session, id, relationships=["project", "genre"])


@router.get("/{id}/children", response_model=List[TaskResponse])
async def get_task_children(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get all child tasks of a parent task."""
    return await service.get_children(session, id)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_create: TaskCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new task."""
    # Convert TaskCreate to Task model
    task = Task(**task_create.model_dump(exclude_unset=True))
    return await service.create(session, task)


@router.patch("/{id}", response_model=TaskResponse)
async def update_task(
    id: int,
    task_update: TaskUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a task (partial update)."""
    return await service.update(session, id, task_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a task."""
    await service.delete(session, id)
