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
