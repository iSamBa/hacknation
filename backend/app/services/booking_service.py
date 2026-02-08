import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.booking import Booking, BookingProvider, BookingStatus
from app.models.call_result import CallResult
from app.models.provider import Provider
from app.schemas.booking import ConfirmBookingResponse, ShortlistItemResponse
from app.schemas.intent import BookingIntent
from app.services.intent_parser import parse_booking_intent
from app.services.scoring import ScoredProvider

logger = logging.getLogger(__name__)


async def create_booking(
    db: AsyncSession,
    user_id: uuid.UUID,
    message: str,
    intent: BookingIntent | None = None,
) -> tuple[Booking, BookingIntent]:
    """Parse intent from message and create a new booking.

    If intent is provided, skip LLM parsing and use it directly.
    """
    if intent is None:
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
        .options(selectinload(Booking.booking_providers))
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())


async def save_shortlist(
    db: AsyncSession,
    booking_id: uuid.UUID,
    scored_providers: list[ScoredProvider],
) -> list[BookingProvider]:
    """Persist scored providers as BookingProvider records.

    Looks up each provider by place_id to get the DB provider_id,
    creates BookingProvider records with rank/score/travel_minutes,
    and updates the booking status to SHORTLISTING.

    Args:
        db: Database session.
        booking_id: The booking to attach providers to.
        scored_providers: Ranked list from the scoring algorithm.

    Returns:
        List of created BookingProvider records.
    """
    if not scored_providers:
        return []

    # Look up Provider records by place_id
    place_ids = [sp.provider.place_id for sp in scored_providers]
    result = await db.execute(
        select(Provider).where(Provider.place_id.in_(place_ids))
    )
    provider_map = {p.place_id: p for p in result.scalars().all()}

    booking_providers: list[BookingProvider] = []
    for rank, scored in enumerate(scored_providers, start=1):
        db_provider = provider_map.get(scored.provider.place_id)
        if db_provider is None:
            logger.warning(
                "Provider %s not found in DB, skipping",
                scored.provider.place_id,
            )
            continue

        bp = BookingProvider(
            booking_id=booking_id,
            provider_id=db_provider.id,
            pre_score=scored.score,
            travel_minutes=scored.travel_minutes,
            rank=rank,
        )
        db.add(bp)
        booking_providers.append(bp)

    # Update booking status
    booking_result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    if booking is not None:
        booking.status = BookingStatus.SHORTLISTING

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "Duplicate BookingProvider entries for booking %s, skipped",
            booking_id,
        )
        return []

    return booking_providers


async def get_shortlist(
    db: AsyncSession,
    booking_id: uuid.UUID,
) -> list[ShortlistItemResponse]:
    """Get the shortlisted providers for a booking, ordered by rank.

    Args:
        db: Database session.
        booking_id: The booking to get the shortlist for.

    Returns:
        List of ShortlistItemResponse ordered by rank.
    """
    result = await db.execute(
        select(BookingProvider)
        .options(joinedload(BookingProvider.provider))
        .where(BookingProvider.booking_id == booking_id)
        .order_by(BookingProvider.rank)
    )
    booking_providers = list(result.scalars().all())

    return [
        ShortlistItemResponse(
            rank=bp.rank,
            provider_name=bp.provider.name,
            provider_phone=bp.provider.phone,
            place_id=bp.provider.place_id,
            rating=bp.provider.rating,
            review_count=bp.provider.review_count,
            travel_minutes=bp.travel_minutes,
            pre_score=bp.pre_score,
            provider_id=bp.provider_id,
            was_called=bp.was_called,
        )
        for bp in booking_providers
    ]


async def confirm_booking(
    db: AsyncSession,
    booking_id: uuid.UUID,
    provider_id: uuid.UUID,
    slot: datetime,
) -> ConfirmBookingResponse:
    """Confirm a booking with the selected provider and slot.

    Args:
        db: Database session.
        booking_id: The booking to confirm.
        provider_id: The chosen provider.
        slot: The chosen appointment slot.

    Returns:
        Confirmation response with booking and provider details.

    Raises:
        ValueError: If booking not found, wrong status, or provider invalid.
    """
    # Load booking with row lock to prevent concurrent confirmations
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        raise ValueError(f"Booking {booking_id} not found")

    # Allow idempotent re-confirmation
    if booking.status == BookingStatus.CONFIRMED:
        # Load provider to return the same response
        result = await db.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if provider is None:
            raise ValueError(f"Provider {provider_id} not found")
        return ConfirmBookingResponse(
            id=booking.id,
            status=booking.status,
            provider_name=provider.name,
            provider_address=provider.address,
            slot=slot,
        )

    if booking.status != BookingStatus.OPTIONS_READY:
        raise ValueError(
            f"Booking must be in options_ready status to confirm, "
            f"current status: {booking.status}"
        )

    # Verify provider was shortlisted for this booking
    result = await db.execute(
        select(BookingProvider)
        .where(
            BookingProvider.booking_id == booking_id,
            BookingProvider.provider_id == provider_id,
        )
    )
    bp = result.scalar_one_or_none()
    if bp is None:
        raise ValueError(
            f"Provider {provider_id} is not in the shortlist for booking {booking_id}"
        )

    # Verify the slot was actually offered by this provider
    result = await db.execute(
        select(CallResult)
        .where(
            CallResult.booking_id == booking_id,
            CallResult.provider_id == provider_id,
            CallResult.available_slot == slot,
        )
    )
    call_result = result.scalar_one_or_none()
    if call_result is None:
        raise ValueError(
            f"Slot {slot} was not offered by provider {provider_id}"
        )

    # Load provider details
    result = await db.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise ValueError(f"Provider {provider_id} not found")

    # Update booking status
    booking.status = BookingStatus.CONFIRMED
    await db.commit()

    logger.info(
        "Booking %s confirmed with provider %s at %s",
        booking_id,
        provider.name,
        slot,
    )

    return ConfirmBookingResponse(
        id=booking.id,
        status=booking.status,
        provider_name=provider.name,
        provider_address=provider.address,
        slot=slot,
    )
