"""Process ElevenLabs post-call webhook data."""

import logging
from datetime import datetime

from dateutil import parser as dateutil_parser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    Returns the updated CallResult, or None if not found.
    """
    result = await db.execute(
        select(CallResult).where(
            CallResult.conversation_id == conversation_id,
        )
    )
    call_result = result.scalar_one_or_none()

    if call_result is None:
        logger.warning(
            "No CallResult found for conversation_id=%s. "
            "Data will be logged but not persisted.",
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
