from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import SettingsResponse, SettingsUpdate

router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return SettingsResponse(
        llm_preference=user.llm_preference,
        settings=user.settings or {},
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.llm_preference is not None:
        user.llm_preference = update.llm_preference

    await db.flush()

    return SettingsResponse(
        llm_preference=user.llm_preference,
        settings=user.settings or {},
    )
