from typing import Any

from pydantic import BaseModel, Field


class CheckCalendarRequest(BaseModel):
    date: str = Field(..., min_length=1)
    time: str = Field(..., min_length=1)


class CheckCalendarResponse(BaseModel):
    available: bool
    conflicts: list[str] = []


class ConfirmSlotRequest(BaseModel):
    date: str = Field(..., min_length=1)
    time: str = Field(..., min_length=1)
    provider_notes: str | None = None


class ConfirmSlotResponse(BaseModel):
    confirmed: bool
    message: str


class PostCallWebhookRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    data_collection: dict[str, Any] = {}
    analysis: dict[str, Any] = {}
    transcript: list[dict[str, Any]] | None = None
    call_duration_seconds: int | None = Field(None, ge=0)


class PostCallWebhookResponse(BaseModel):
    status: str
