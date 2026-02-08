import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus
from app.schemas.intent import BookingIntent


class BookingRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class BookingRequestResponse(BaseModel):
    booking_id: uuid.UUID
    status: BookingStatus
    intent: BookingIntent

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    user_id: uuid.UUID
    status: BookingStatus = BookingStatus.SEARCHING
    service_type: str = Field(..., max_length=255)
    preferred_date: str | None = Field(None, max_length=50)
    preferred_time: str | None = Field(None, max_length=50)
    location_override: str | None = Field(None, max_length=500)
    constraints: dict[str, Any] | None = None
    raw_message: str


class BookingUpdate(BaseModel):
    status: BookingStatus | None = None
    service_type: str | None = Field(None, max_length=255)
    preferred_date: str | None = Field(None, max_length=50)
    preferred_time: str | None = Field(None, max_length=50)
    location_override: str | None = Field(None, max_length=500)
    constraints: dict[str, Any] | None = None


class BookingResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: BookingStatus
    service_type: str
    preferred_date: str | None
    preferred_time: str | None
    location_override: str | None
    constraints: Any | None
    raw_message: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingProviderCreate(BaseModel):
    booking_id: uuid.UUID
    provider_id: uuid.UUID
    pre_score: float = Field(..., ge=0)
    travel_minutes: float | None = Field(None, ge=0)
    was_called: bool = False
    rank: int | None = Field(None, ge=1)


class BookingProviderUpdate(BaseModel):
    pre_score: float | None = Field(None, ge=0)
    travel_minutes: float | None = Field(None, ge=0)
    was_called: bool | None = None
    rank: int | None = Field(None, ge=1)


class BookingProviderResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    provider_id: uuid.UUID
    pre_score: float
    travel_minutes: float | None
    was_called: bool
    rank: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
