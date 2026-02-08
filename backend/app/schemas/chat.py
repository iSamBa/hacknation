import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus
from app.schemas.intent import BookingIntent


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryMessage] = []


class ChatMessageResponse(BaseModel):
    is_booking_request: bool
    reply: str
    booking_id: uuid.UUID | None = None
    status: BookingStatus | None = None
    intent: BookingIntent | None = None
