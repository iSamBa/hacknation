import uuid
from enum import StrEnum

from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BookingStatus(StrEnum):
    SEARCHING = "searching"
    SHORTLISTING = "shortlisting"
    CALLING = "calling"
    COLLECTING = "collecting"
    RANKING = "ranking"
    OPTIONS_READY = "options_ready"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    CALL_FAILED = "call_failed"


class Booking(Base):
    __tablename__ = "bookings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, values_callable=lambda e: [m.value for m in e]),
        server_default=text("'searching'"),
        default=BookingStatus.SEARCHING,
    )
    service_type: Mapped[str] = mapped_column(String(255))
    preferred_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location_override: Mapped[str | None] = mapped_column(String(500), nullable=True)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_message: Mapped[str] = mapped_column(Text)

    user = relationship("UserProfile", backref="bookings")
    booking_providers = relationship("BookingProvider", back_populates="booking")


class BookingProvider(Base):
    __tablename__ = "booking_providers"
    __table_args__ = (
        UniqueConstraint("booking_id", "provider_id", name="uq_booking_provider"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), index=True
    )
    pre_score: Mapped[float] = mapped_column(Float)
    travel_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    was_called: Mapped[bool] = mapped_column(
        server_default=text("false"), default=False
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    booking = relationship("Booking", back_populates="booking_providers")
    provider = relationship("Provider", backref="booking_providers")
