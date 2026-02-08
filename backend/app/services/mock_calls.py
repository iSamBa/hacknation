"""Mock call results for testing the full pipeline without actual calls."""

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingProvider
from app.models.call_result import CallOutcome, CallResult

logger = logging.getLogger(__name__)

# Weighted outcomes: ~60% offered, ~10% tentative, ~20% unavailable, ~10% VM
_OUTCOME_WEIGHTS: list[tuple[CallOutcome, float]] = [
    (CallOutcome.SLOT_OFFERED, 0.6),
    (CallOutcome.BOOKED_TENTATIVE, 0.1),
    (CallOutcome.NO_AVAILABILITY, 0.2),
    (CallOutcome.VOICEMAIL, 0.1),
]

_OUTCOMES = [o for o, _ in _OUTCOME_WEIGHTS]
_WEIGHTS = [w for _, w in _OUTCOME_WEIGHTS]

_MOCK_NOTES = [
    None,
    "New patients welcome",
    "Requires referral",
    "Cash only",
    "Insurance accepted",
    None,
]


async def generate_mock_call_results(
    db: AsyncSession,
    booking_id: uuid.UUID,
    booking_providers: list[BookingProvider],
) -> list[CallResult]:
    """Simulate call outcomes for shortlisted providers.

    Creates ``CallResult`` records and updates each BookingProvider's
    ``was_called`` flag to ``True``.

    Args:
        db: Database session.
        booking_id: The booking these providers belong to.
        booking_providers: The shortlisted BookingProvider records.

    Returns:
        The created CallResult records.
    """
    if not booking_providers:
        logger.info("No providers to call for booking %s", booking_id)
        return []

    now = datetime.now(timezone.utc)
    call_results: list[CallResult] = []

    for bp in booking_providers:
        outcome = random.choices(_OUTCOMES, weights=_WEIGHTS, k=1)[0]  # noqa: S311
        bp.was_called = True

        # Generate a slot for positive outcomes
        available_slot = None
        if outcome in (CallOutcome.SLOT_OFFERED, CallOutcome.BOOKED_TENTATIVE):
            days_ahead = random.randint(1, 14)  # noqa: S311
            hour = random.choice([9, 10, 11, 14, 15, 16])  # noqa: S311
            available_slot = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=0, second=0, microsecond=0, tzinfo=None
            )

        notes = random.choice(_MOCK_NOTES)  # noqa: S311
        if outcome != CallOutcome.VOICEMAIL:
            call_duration = random.randint(30, 180)  # noqa: S311
        else:
            call_duration = 15

        naive_now = now.replace(tzinfo=None)
        cr = CallResult(
            booking_id=booking_id,
            provider_id=bp.provider_id,
            call_outcome=outcome,
            available_slot=available_slot,
            provider_notes=notes,
            call_duration_seconds=call_duration,
            started_at=naive_now - timedelta(seconds=call_duration),
            ended_at=naive_now,
        )
        db.add(cr)
        call_results.append(cr)

        logger.info(
            "Mock call result for provider %s: %s (slot=%s)",
            bp.provider_id,
            outcome.value,
            available_slot,
        )

    await db.commit()
    logger.info(
        "Generated mock call results for %d providers on booking %s",
        len(booking_providers),
        booking_id,
    )
    return call_results
