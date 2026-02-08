import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.schemas.intent import BookingIntent
from app.services.intent_parser import parse_booking_intent


async def create_booking(
    db: AsyncSession, user_id: uuid.UUID, message: str
) -> tuple[Booking, BookingIntent]:
    """Parse intent from message and create a new booking."""
    intent = await parse_booking_intent(message)

    booking = Booking(
        user_id=user_id,
        status=BookingStatus.SEARCHING,
        service_type=intent.service_type,
        preferred_date=intent.date,
        preferred_time=intent.time_preference,
        location_override=intent.location_override,
        constraints=intent.constraints if intent.constraints else None,
        raw_message=message,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return booking, intent


async def get_booking(
    db: AsyncSession, booking_id: uuid.UUID
) -> Booking | None:
    """Get a booking by ID."""
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


async def list_bookings(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Booking]:
    """List all bookings for a user, most recent first."""
    result = await db.execute(
        select(Booking)
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())
