from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models import Setting, SettingUpdate
from app.schemas.responses import SettingResponse
from app.exceptions import NotFoundException

router = APIRouter()


@router.get("", response_model=List[SettingResponse])
async def list_settings(
    session: AsyncSession = Depends(get_session),
):
    """Get all settings."""
    query = select(Setting).order_by(Setting.key)
    result = await session.execute(query)
    items = result.scalars().all()
    return items


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """Get setting by key."""
    query = select(Setting).where(Setting.key == key)
    result = await session.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        raise NotFoundException(f"Setting with key '{key}' not found")

    return setting


@router.put("/{key}", response_model=SettingResponse)
async def upsert_setting(
    key: str,
    value: str,
    description: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Update or create setting (upsert)."""
    # Try to find existing setting
    query = select(Setting).where(Setting.key == key)
    result = await session.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        existing.value = value
        if description is not None:
            existing.description = description
        setting = existing
    else:
        # Create new
        setting = Setting(key=key, value=value, description=description)
        session.add(setting)

    await session.commit()
    await session.refresh(setting)
    return setting


@router.patch("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_update: SettingUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update setting by key (partial update)."""
    query = select(Setting).where(Setting.key == key)
    result = await session.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        raise NotFoundException(f"Setting with key '{key}' not found")

    # Update fields that are set (not None)
    update_data = setting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)

    session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete setting by key."""
    query = select(Setting).where(Setting.key == key)
    result = await session.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        raise NotFoundException(f"Setting with key '{key}' not found")

    await session.delete(setting)
    await session.commit()
