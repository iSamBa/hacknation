import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    place_id: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    address: str = Field(..., max_length=500)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    phone: str | None = Field(None, max_length=50)
    rating: float = Field(..., ge=0.0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    is_open: bool | None = None


class ProviderUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    phone: str | None = Field(None, max_length=50)
    rating: float | None = Field(None, ge=0.0, le=5.0)
    review_count: int | None = Field(None, ge=0)
    is_open: bool | None = None


class ProviderResponse(BaseModel):
    id: uuid.UUID
    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    phone: str | None
    rating: float
    review_count: int
    is_open: bool | None
    cached_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
