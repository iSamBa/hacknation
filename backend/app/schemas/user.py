import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserProfileCreate(BaseModel):
    name: str = Field(..., max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str = Field(..., max_length=500)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    preferred_times: list[str] = Field(default_factory=list)
    preferred_days: list[str] = Field(default_factory=list)
    avoid_times: list[str] | None = None
    max_distance_km: float = Field(default=10.0, gt=0)
    min_rating: float = Field(default=4.0, ge=0.0, le=5.0)
    preferred_providers: list[str] = Field(default_factory=list)
    blocked_providers: list[str] = Field(default_factory=list)
    language_preference: str = "english"
    google_calendar_id: str | None = None


class UserProfileUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    preferred_times: list[str] | None = None
    preferred_days: list[str] | None = None
    avoid_times: list[str] | None = None
    max_distance_km: float | None = Field(None, gt=0)
    min_rating: float | None = Field(None, ge=0.0, le=5.0)
    preferred_providers: list[str] | None = None
    blocked_providers: list[str] | None = None
    language_preference: str | None = None
    google_calendar_id: str | None = None


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    address: str
    latitude: float
    longitude: float
    preferred_times: list[str]
    preferred_days: list[str]
    avoid_times: list[str] | None
    max_distance_km: float
    min_rating: float
    preferred_providers: list[str]
    blocked_providers: list[str]
    language_preference: str
    google_calendar_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
