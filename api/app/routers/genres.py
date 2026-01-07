from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models import Genre, GenreUpdate
from app.services.base import BaseCRUDService
from app.schemas.common import PaginatedResponse, GenreCreate
from app.schemas.responses import GenreResponse
from app.dependencies import CommonQueryParams

router = APIRouter()
service = BaseCRUDService[Genre, GenreUpdate](Genre)


@router.get("", response_model=PaginatedResponse[GenreResponse])
async def list_genres(
    commons: CommonQueryParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """Get all genres with pagination."""
    items, total = await service.get_all(
        session, skip=commons.skip, limit=commons.limit, order_by=commons.sort or "name"
    )

    return PaginatedResponse(
        items=items, total=total, skip=commons.skip, limit=commons.limit
    )


@router.get("/{id}", response_model=GenreResponse)
async def get_genre(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single genre by ID."""
    return await service.get_by_id(session, id)


@router.post("", response_model=GenreResponse, status_code=status.HTTP_201_CREATED)
async def create_genre(
    genre_in: GenreCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new genre."""
    genre = Genre(**genre_in.model_dump())
    return await service.create(session, genre)


@router.patch("/{id}", response_model=GenreResponse)
async def update_genre(
    id: int,
    genre_update: GenreUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a genre (partial update)."""
    return await service.update(session, id, genre_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_genre(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a genre."""
    await service.delete(session, id)
