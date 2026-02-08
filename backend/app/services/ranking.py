"""Post-call ranking algorithm.

Combines pre-call provider score with actual call outcomes
to produce a final ranking of providers for the user.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingProvider
from app.models.call_result import CallOutcome, CallResult
from app.models.provider import Provider

logger = logging.getLogger(__name__)

# Post-call ranking weights
W_PRE_SCORE = 0.30
W_EARLIEST_SLOT = 0.30
W_SLOT_MATCH = 0.25
W_NOTES = 0.15

# Normalisation bounds
MAX_DAYS_AHEAD = 14

# Only these outcomes indicate the provider has availability
_POSITIVE_OUTCOMES = frozenset({CallOutcome.SLOT_OFFERED, CallOutcome.BOOKED_TENTATIVE})

DEFAULT_TOP_N = 5


def earliest_score(slot: datetime, max_days: int = MAX_DAYS_AHEAD) -> float:
    """Score 0-1: sooner slots score higher. Slots beyond *max_days* score 0."""
    now = datetime.now(timezone.utc)
    if slot.tzinfo is None:
        slot = slot.replace(tzinfo=timezone.utc)
    delta = slot - now
    days_until = delta.total_seconds() / 86400
    if days_until <= 0:
        return 1.0
    return max(0.0, 1.0 - days_until / max_days)


def slot_match_score(
    slot: datetime,
    preferred_date: str | None,
    preferred_time: str | None,
) -> float:
    """Score 0-1: how well the offered slot matches the user's preference.

    - Exact date + time match → 1.0
    - Same date, different time → 0.5
    - Different date → 0.25
    - No preference specified → 0.5 (neutral)
    """
    if not preferred_date and not preferred_time:
        return 0.5

    date_match = False
    time_match = False

    if preferred_date:
        try:
            wanted = datetime.strptime(preferred_date, "%Y-%m-%d").date()
            date_match = slot.date() == wanted
        except ValueError:
            # Relative dates like "tomorrow" — treat as partial match
            date_match = False

    if preferred_time:
        slot_hour = slot.hour
        time_lower = preferred_time.lower()
        if time_lower == "morning":
            time_match = 6 <= slot_hour < 12
        elif time_lower == "afternoon":
            time_match = 12 <= slot_hour < 17
        elif time_lower == "evening":
            time_match = 17 <= slot_hour < 21
        else:
            # Try parsing as HH:MM
            try:
                wanted_hour = int(time_lower.split(":")[0])
                time_match = abs(slot_hour - wanted_hour) <= 1
            except (ValueError, IndexError):
                time_match = False

    if date_match and time_match:
        return 1.0
    if date_match:
        return 0.5
    if time_match:
        return 0.5
    return 0.25


def notes_score(notes: str | None) -> float:
    """Score 0-1: no restrictions/notes = 1.0, notes present = 0.5.

    Notes that mention restrictions reduce the score.
    """
    if not notes:
        return 1.0

    lower = notes.lower()
    restriction_keywords = {"referral", "cash only", "restriction", "required"}
    if any(kw in lower for kw in restriction_keywords):
        return 0.3

    return 0.7


class RankedResult:
    """A ranked provider result combining call outcome with scoring."""

    __slots__ = (
        "call_outcome",
        "notes",
        "place_id",
        "provider_id",
        "provider_name",
        "rank",
        "rating",
        "review_count",
        "score",
        "slot",
        "travel_minutes",
    )

    def __init__(
        self,
        *,
        rank: int,
        provider_id: uuid.UUID,
        provider_name: str,
        place_id: str,
        slot: datetime,
        travel_minutes: float | None,
        rating: float,
        review_count: int,
        score: float,
        notes: str | None,
        call_outcome: str,
    ) -> None:
        self.rank = rank
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.place_id = place_id
        self.slot = slot
        self.travel_minutes = travel_minutes
        self.rating = rating
        self.review_count = review_count
        self.score = score
        self.notes = notes
        self.call_outcome = call_outcome


async def rank_results(
    db: AsyncSession,
    booking_id: uuid.UUID,
    top_n: int = DEFAULT_TOP_N,
) -> list[RankedResult]:
    """Rank providers based on call results and pre-call scores.

    Args:
        db: Database session.
        booking_id: The booking to rank results for.
        top_n: Maximum number of results to return.

    Returns:
        Providers sorted by final score descending, limited to *top_n*.

    Raises:
        ValueError: If the booking is not found.
    """
    # Load booking for preference data
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        msg = f"Booking {booking_id} not found"
        raise ValueError(msg)

    # Load call results with positive outcomes
    result = await db.execute(
        select(CallResult)
        .options(selectinload(CallResult.provider))
        .where(
            CallResult.booking_id == booking_id,
            CallResult.call_outcome.in_([o.value for o in _POSITIVE_OUTCOMES]),
            CallResult.available_slot.is_not(None),
        )
    )
    call_results = list(result.scalars().all())

    if not call_results:
        logger.info("No positive call results for booking %s", booking_id)
        return []

    # Build provider_id → BookingProvider map for pre_score & travel data
    bp_result = await db.execute(
        select(BookingProvider).where(BookingProvider.booking_id == booking_id)
    )
    bp_map: dict[uuid.UUID, BookingProvider] = {
        bp.provider_id: bp for bp in bp_result.scalars().all()
    }

    # Score each call result
    scored: list[tuple[float, CallResult, BookingProvider]] = []
    for cr in call_results:
        bp = bp_map.get(cr.provider_id)
        if bp is None or cr.available_slot is None:
            continue

        # Normalize pre_score to 0-1 (it's already roughly in that range)
        pre = min(1.0, max(0.0, bp.pre_score))

        earliest = earliest_score(cr.available_slot)
        match = slot_match_score(
            cr.available_slot,
            booking.preferred_date,
            booking.preferred_time,
        )
        notes_s = notes_score(cr.provider_notes)

        final = (
            pre * W_PRE_SCORE
            + earliest * W_EARLIEST_SLOT
            + match * W_SLOT_MATCH
            + notes_s * W_NOTES
        )

        scored.append((round(final, 4), cr, bp))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Build ranked results
    results: list[RankedResult] = []
    for i, (score, cr, bp) in enumerate(scored[:top_n], start=1):
        provider: Provider = cr.provider

        results.append(
            RankedResult(
                rank=i,
                provider_id=provider.id,
                provider_name=provider.name,
                place_id=provider.place_id,
                slot=cr.available_slot,
                travel_minutes=bp.travel_minutes,
                rating=provider.rating,
                review_count=provider.review_count,
                score=score,
                notes=cr.provider_notes,
                call_outcome=cr.call_outcome.value,
            )
        )

    # Update BookingProvider.rank for the ranked results
    for r in results:
        bp = bp_map.get(r.provider_id)
        if bp is not None:
            bp.rank = r.rank
    await db.commit()

    logger.info(
        "Ranked %d results for booking %s (from %d call results)",
        len(results),
        booking_id,
        len(call_results),
    )
    return results
