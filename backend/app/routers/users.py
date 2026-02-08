from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.user import UserProfileResponse, UserProfileUpdate
from app.services.user_service import get_or_create_default_user, update_user_profile

router = APIRouter(prefix="/api/users", tags=["users"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(db: DbSession):
    user = await get_or_create_default_user(db)
    return user


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user(data: UserProfileUpdate, db: DbSession):
    user = await get_or_create_default_user(db)
    return await update_user_profile(db, user.id, data)
