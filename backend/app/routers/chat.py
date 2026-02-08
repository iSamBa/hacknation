from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.booking_service import create_booking
from app.services.intent_parser import classify_and_parse
from app.services.pipeline import start_pipeline
from app.services.user_service import get_or_create_default_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=ChatMessageResponse)
async def chat_endpoint(body: ChatMessageRequest, db: DbSession):
    user = await get_or_create_default_user(db)

    history = [msg.model_dump() for msg in body.history]

    try:
        chat_response = await classify_and_parse(
            body.message,
            history=history,
            user_name=user.name,
            preferred_times=user.preferred_times or None,
            preferred_days=user.preferred_days or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Save user's name if they provided it
    if chat_response.user_name and chat_response.user_name != user.name:
        user.name = chat_response.user_name
        await db.commit()
        await db.refresh(user)

    # Don't start a booking until we have the user's name
    name_known = user.name and user.name != "Default User"
    if not chat_response.is_booking_request or not name_known:
        return ChatMessageResponse(
            is_booking_request=False,
            reply=chat_response.reply,
        )

    intent = chat_response.to_booking_intent()
    try:
        booking, _ = await create_booking(db, user.id, body.message, intent)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    start_pipeline(booking.id)
    return ChatMessageResponse(
        is_booking_request=True,
        reply=chat_response.reply,
        booking_id=booking.id,
        status=booking.status,
        intent=intent,
    )
