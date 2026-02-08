"""Mock call results for testing the full pipeline without actual calls."""

import logging
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingProvider

logger = logging.getLogger(__name__)

# Possible outcomes when "calling" a provider
CALL_OUTCOMES = [
    "slot_available",
    "slot_available",
    "slot_available",
    "unavailable",
    "voicemail",
]


async def generate_mock_call_results(
    db: AsyncSession,
    booking_id: uuid.UUID,
    booking_providers: list[BookingProvider],
) -> list[BookingProvider]:
    """Simulate call outcomes for shortlisted providers.

    Updates each BookingProvider's ``was_called`` flag to ``True``.
    In a real implementation, this would be replaced by actual outbound
    calling logic that records availability, offered slots, etc.

    Args:
        db: Database session.
        booking_id: The booking these providers belong to.
        booking_providers: The shortlisted BookingProvider records.

    Returns:
        The updated BookingProvider records with ``was_called = True``.
    """
    if not booking_providers:
        logger.info("No providers to call for booking %s", booking_id)
        return []

    for bp in booking_providers:
        outcome = random.choice(CALL_OUTCOMES)  # noqa: S311
        bp.was_called = True
        logger.info(
            "Mock call result for provider %s: %s",
            bp.provider_id,
            outcome,
        )

    await db.commit()
    logger.info(
        "Generated mock call results for %d providers on booking %s",
        len(booking_providers),
        booking_id,
    )
    return booking_providers
