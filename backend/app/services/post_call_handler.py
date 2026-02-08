"""Process ElevenLabs post-call webhook data."""

import logging
from datetime import datetime

from dateutil import parser as dateutil_parser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket_manager import ws_manager
from app.models.booking import Booking, BookingStatus
from app.models.call_result import CallOutcome, CallResult

logger = logging.getLogger(__name__)

# Map ElevenLabs data_collection outcomes to our CallOutcome enum
_OUTCOME_MAP: dict[str, CallOutcome] = {
    "slot_offered": CallOutcome.SLOT_OFFERED,
    "no_availability": CallOutcome.NO_AVAILABILITY,
    "voicemail": CallOutcome.VOICEMAIL,
    "call_failed": CallOutcome.CALL_FAILED,
}


def parse_slot(slot_str: str | None) -> datetime | None:
    """Parse a natural-language slot string into a datetime.

    Handles formats like "Tuesday 2pm", "February 10th at 14:00",
    and ISO formats. Returns None if parsing fails or input is empty.
    """
    if not slot_str or not slot_str.strip():
        return None
    try:
        return dateutil_parser.parse(slot_str, fuzzy=True)
    except (ValueError, OverflowError):
        logger.warning("Could not parse slot string: %s", slot_str)
        return None


async def update_call_result_from_webhook(
    db: AsyncSession,
    conversation_id: str,
    data_collection: dict,
    analysis: dict,
    transcript: list | dict | None = None,
    call_duration_seconds: int | None = None,
) -> CallResult | None:
    """Update an existing CallResult with post-call webhook data.

    Looks up the CallResult by conversation_id and updates it with
    extracted data collection fields and analysis results.

    If no CallResult exists, tries to create one by finding the most recent
    CALLING booking (DEMO MODE for widget-based conversations).

    Returns the updated CallResult, or None if not found.
    """
    result = await db.execute(
        select(CallResult).where(
            CallResult.conversation_id == conversation_id,
        )
    )
    call_result = result.scalar_one_or_none()

    # DEMO MODE: If no CallResult exists, try to find the calling booking and create one
    if call_result is None:
        logger.info(
            "No CallResult found for conversation_id=%s. "
            "Attempting to create one for DEMO MODE (widget conversation).",
            conversation_id,
        )

        # Find the most recent booking in CALLING status
        booking_result = await db.execute(
            select(Booking)
            .where(Booking.status == BookingStatus.CALLING)
            .order_by(Booking.created_at.desc())
            .limit(1)
        )
        booking = booking_result.scalar_one_or_none()

        if booking:
            # Get the top-ranked provider from this booking
            from app.models.booking import BookingProvider

            provider_result = await db.execute(
                select(BookingProvider)
                .where(
                    BookingProvider.booking_id == booking.id,
                    BookingProvider.rank == 1,
                )
            )
            booking_provider = provider_result.scalar_one_or_none()

            if booking_provider:
                # Create new CallResult for this widget conversation
                naive_now = datetime.now().replace(tzinfo=None)
                call_result = CallResult(
                    booking_id=booking.id,
                    provider_id=booking_provider.provider_id,
                    conversation_id=conversation_id,
                    call_outcome=CallOutcome.CALL_FAILED,  # Will be updated below
                    started_at=naive_now,
                    ended_at=naive_now,
                )
                db.add(call_result)

                # Mark provider as called
                booking_provider.was_called = True
                await db.commit()
                await db.refresh(call_result)

                logger.info(
                    "Created CallResult for widget conversation_id=%s, booking=%s",
                    conversation_id,
                    booking.id,
                )
            else:
                logger.warning("No rank=1 provider found for booking %s", booking.id)
                _log_analysis(conversation_id, analysis)
                return None
        else:
            logger.warning(
                "No booking in CALLING status found for conversation_id=%s",
                conversation_id,
            )
            _log_analysis(conversation_id, analysis)
            return None

    # Update call outcome
    raw_outcome = data_collection.get("call_outcome", "")
    outcome = _OUTCOME_MAP.get(raw_outcome)
    if outcome is not None:
        call_result.call_outcome = outcome

    # Update available slot
    slot = parse_slot(data_collection.get("available_slot"))
    if slot is not None:
        call_result.available_slot = slot

    # Update provider notes
    notes = data_collection.get("provider_notes")
    if notes:
        call_result.provider_notes = notes

    # Update transcript and duration
    if transcript is not None:
        call_result.transcript = (
            transcript if isinstance(transcript, dict)
            else {"messages": transcript}
        )
    if call_duration_seconds is not None:
        call_result.call_duration_seconds = call_duration_seconds

    await db.commit()
    await db.refresh(call_result)

    # Notify frontend via WebSocket
    await ws_manager.send_to_booking(
        call_result.booking_id,
        {
            "type": "call_result_updated",
            "booking_id": str(call_result.booking_id),
            "provider_id": str(call_result.provider_id),
            "outcome": call_result.call_outcome.value,
        },
    )

    # Auto-transition booking after call completes
    booking_result = await db.execute(
        select(Booking).where(Booking.id == call_result.booking_id)
    )
    booking = booking_result.scalar_one_or_none()

    if booking and booking.status == BookingStatus.CALLING:
        # If appointment was successfully booked (SLOT_OFFERED), go straight to CONFIRMED
        # Otherwise, go to OPTIONS_READY
        if call_result.call_outcome == CallOutcome.SLOT_OFFERED:
            booking.status = BookingStatus.CONFIRMED
            new_status = BookingStatus.CONFIRMED.value

            logger.info(
                "Auto-transitioned booking %s to CONFIRMED (appointment booked during call)",
                call_result.booking_id,
            )
        else:
            booking.status = BookingStatus.OPTIONS_READY
            new_status = BookingStatus.OPTIONS_READY.value

            logger.info(
                "Auto-transitioned booking %s to OPTIONS_READY (no appointment booked)",
                call_result.booking_id,
            )

        await db.commit()

        # Notify frontend of status change
        await ws_manager.send_to_booking(
            call_result.booking_id,
            {
                "type": "status",
                "status": new_status,
                "booking_id": str(call_result.booking_id),
            },
        )

    _log_analysis(conversation_id, analysis)
    logger.info(
        "Updated CallResult %s from post-call webhook "
        "(outcome=%s, slot=%s)",
        call_result.id, call_result.call_outcome,
        call_result.available_slot,
    )
    return call_result


def _log_analysis(
    conversation_id: str, analysis: dict,
) -> None:
    """Log conversation analysis results for monitoring."""
    if not analysis:
        return
    logger.info(
        "Analysis for conversation %s: %s",
        conversation_id, analysis,
    )
