import uuid

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus
from app.schemas.intent import BookingIntent


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatMessageResponse(BaseModel):
    is_booking_request: bool
    reply: str
    booking_id: uuid.UUID | None = None
    status: BookingStatus | None = None
    intent: BookingIntent | None = None
