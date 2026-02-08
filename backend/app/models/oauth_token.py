"""OAuth token model for storing user calendar credentials."""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50))  # "google"
    access_token: Mapped[str] = mapped_column(String(2000))  # encrypted
    refresh_token: Mapped[str] = mapped_column(String(2000))  # encrypted
    token_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    user = relationship("UserProfile", back_populates="oauth_tokens")
