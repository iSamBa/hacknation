from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.booking_service import create_booking
from app.services.intent_parser import classify_and_parse
from app.services.user_service import get_or_create_default_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=ChatMessageResponse)
async def chat_endpoint(body: ChatMessageRequest, db: DbSession):
    user = await get_or_create_default_user(db)

    try:
        chat_response = await classify_and_parse(body.message)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    if not chat_response.is_booking_request:
        return ChatMessageResponse(
            is_booking_request=False,
            reply=chat_response.reply,
        )

    intent = chat_response.to_booking_intent()
    try:
        booking, _ = await create_booking(db, user.id, body.message, intent)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return ChatMessageResponse(
        is_booking_request=True,
        reply=chat_response.reply,
        booking_id=booking.id,
        status=booking.status,
        intent=intent,
    )
