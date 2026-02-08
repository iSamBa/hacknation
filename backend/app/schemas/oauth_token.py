"""OAuth token response schemas - never expose raw tokens."""

from datetime import datetime

from pydantic import BaseModel


class OAuthTokenStatus(BaseModel):
    """OAuth connection status - never includes actual token values."""

    provider: str
    connected: bool
    scopes: list[str]
    connected_at: datetime | None = None

    model_config = {"from_attributes": True}
