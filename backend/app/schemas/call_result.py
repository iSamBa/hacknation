import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.call_result import CallOutcome


class CallResultCreate(BaseModel):
    booking_id: uuid.UUID
    provider_id: uuid.UUID
    conversation_id: str | None = Field(None, max_length=255)
    call_outcome: CallOutcome
    available_slot: datetime | None = None
    provider_notes: str | None = None
    transcript: dict[str, Any] | None = None
    call_duration_seconds: int | None = Field(None, ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class CallResultUpdate(BaseModel):
    call_outcome: CallOutcome | None = None
    available_slot: datetime | None = None
    provider_notes: str | None = None
    transcript: dict[str, Any] | None = None
    call_duration_seconds: int | None = Field(None, ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class CallResultResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    provider_id: uuid.UUID
    conversation_id: str | None
    call_outcome: CallOutcome
    available_slot: datetime | None
    provider_notes: str | None
    transcript: dict[str, Any] | None
    call_duration_seconds: int | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
