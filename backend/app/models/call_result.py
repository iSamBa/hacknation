import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CallOutcome(StrEnum):
    SLOT_OFFERED = "slot_offered"
    BOOKED_TENTATIVE = "booked_tentative"
    NO_AVAILABILITY = "no_availability"
    VOICEMAIL = "voicemail"
    CALL_FAILED = "call_failed"
    CANCELLED = "cancelled"


class CallResult(Base):
    __tablename__ = "call_results"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_outcome: Mapped[CallOutcome] = mapped_column(
        Enum(CallOutcome, values_callable=lambda e: [m.value for m in e])
    )
    available_slot: Mapped[datetime | None] = mapped_column(nullable=True)
    provider_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    call_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    booking = relationship("Booking", backref="call_results")
    provider = relationship("Provider", backref="call_results")
