from sqlalchemy import ARRAY, Float, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(String(500))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    preferred_times: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default=text("'{}'"), default=list
    )
    preferred_days: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default=text("'{}'"), default=list
    )
    avoid_times: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    max_distance_km: Mapped[float] = mapped_column(
        Float, server_default=text("10.0"), default=10.0
    )
    min_rating: Mapped[float] = mapped_column(
        Float, server_default=text("4.0"), default=4.0
    )
    shortlist_count: Mapped[int] = mapped_column(
        server_default=text("15"), default=15
    )
    preferred_providers: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default=text("'{}'"), default=list
    )
    blocked_providers: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default=text("'{}'"), default=list
    )
    language_preference: Mapped[str] = mapped_column(
        String(50), server_default=text("'english'"), default="english"
    )
    transport_mode: Mapped[str] = mapped_column(
        String(20), server_default=text("'driving'"), default="driving"
    )
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    oauth_tokens = relationship(
        "OAuthToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
