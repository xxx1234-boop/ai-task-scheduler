from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models import Project, ProjectUpdate
from app.services.base import BaseCRUDService
from app.schemas.common import PaginatedResponse
from app.schemas.responses import ProjectResponse
from app.dependencies import CommonQueryParams

router = APIRouter()
service = BaseCRUDService[Project, ProjectUpdate](Project)


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    commons: CommonQueryParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """Get all projects with pagination."""
    items, total = await service.get_all(
        session, skip=commons.skip, limit=commons.limit, order_by=commons.sort or "-created_at"
    )

    return PaginatedResponse(
        items=items, total=total, skip=commons.skip, limit=commons.limit
    )


@router.get("/{id}", response_model=ProjectResponse)
async def get_project(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single project by ID."""
    return await service.get_by_id(session, id)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: Project,
    session: AsyncSession = Depends(get_session),
):
    """Create a new project."""
    return await service.create(session, project)


@router.patch("/{id}", response_model=ProjectResponse)
async def update_project(
    id: int,
    project_update: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a project (partial update)."""
    return await service.update(session, id, project_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a project."""
    await service.delete(session, id)
