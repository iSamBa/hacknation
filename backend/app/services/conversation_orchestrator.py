"""Orchestrates ElevenLabs conversations for booking providers."""

import base64
import logging
import uuid
from datetime import datetime, timezone
from functools import partial

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.conversation_manager import conversation_manager
from app.core.websocket_manager import ws_manager
from app.models.booking import Booking, BookingProvider
from app.models.call_result import CallOutcome, CallResult
from app.models.provider import Provider
from app.models.user import UserProfile
from app.services.elevenlabs_client import (
    ConversationConnectionError,
    ConversationTimeoutError,
    ElevenLabsConversation,
)

logger = logging.getLogger(__name__)


async def _send_audio_chunk(
    audio_bytes: bytes,
    booking_id: uuid.UUID,
    provider_id: uuid.UUID,
) -> None:
    """Send audio chunk to frontend via WebSocket."""
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    await ws_manager.send_to_booking(
        booking_id,
        {
            "type": "conversation_audio",
            "booking_id": str(booking_id),
            "provider_id": str(provider_id),
            "audio": audio_base64,
            "format": "pcm_16000",
        },
    )


async def _send_event(
    event_type: str,
    text: str,
    booking_id: uuid.UUID,
    provider_id: uuid.UUID,
) -> None:
    """Send conversation event (transcript) to frontend via WebSocket."""
    await ws_manager.send_to_booking(
        booking_id,
        {
            "type": "conversation_event",
            "booking_id": str(booking_id),
            "provider_id": str(provider_id),
            "event_type": event_type,
            "text": text,
        },
    )


async def run_conversations_for_booking(
    db: AsyncSession,
    booking_id: uuid.UUID,
    booking_providers: list[BookingProvider],
) -> list[CallResult]:
    """Run ElevenLabs conversations for all providers sequentially.

    For each provider:
    1. Create CallResult with conversation_id and started_at
    2. Build dynamic variables from booking/user/provider data
    3. Notify frontend via WebSocket (conversation_started)
    4. Initiate ElevenLabsConversation
    5. Stream audio/events to frontend
    6. Wait for conversation end or timeout
    7. Update CallResult.ended_at

    Note: The final outcome, slot, and notes are populated later by the
    post-call webhook handler.

    Args:
        db: Database session
        booking_id: Booking UUID
        booking_providers: List of BookingProvider records to call

    Returns:
        List of created CallResult records
    """
    if not booking_providers:
        logger.info("No providers to call for booking %s", booking_id)
        return []

    # Load booking with user and all relationships
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.user))
        .where(Booking.id == booking_id)
    )
    booking = result.scalar_one()

    call_results: list[CallResult] = []

    for bp in booking_providers:
        # Load provider
        provider_result = await db.execute(
            select(Provider).where(Provider.id == bp.provider_id)
        )
        provider = provider_result.scalar_one()

        # Generate conversation ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        conversation_id = f"{booking_id}_{provider.id}_{timestamp}"

        # Build dynamic variables for the agent
        dynamic_vars = _build_dynamic_variables(booking, booking.user, provider)

        # Create CallResult record (outcome will be set by webhook)
        naive_now = datetime.now(timezone.utc).replace(tzinfo=None)
        call_result = CallResult(
            booking_id=booking_id,
            provider_id=provider.id,
            conversation_id=conversation_id,
            call_outcome=CallOutcome.CALL_FAILED,  # Default, updated by webhook
            started_at=naive_now,
        )
        db.add(call_result)
        await db.commit()
        await db.refresh(call_result)
        call_results.append(call_result)

        # Mark provider as called
        bp.was_called = True
        await db.commit()

        logger.info(
            "Starting conversation %s for provider %s (%s)",
            conversation_id,
            provider.id,
            provider.name,
        )

        # Notify frontend: conversation started
        await ws_manager.send_to_booking(
            booking_id,
            {
                "type": "conversation_started",
                "booking_id": str(booking_id),
                "provider_id": str(provider.id),
                "provider_name": provider.name,
                "conversation_id": conversation_id,
            },
        )

        # Create conversation client
        conversation = ElevenLabsConversation(
            conversation_id=conversation_id,
            booking_id=booking_id,
            provider_id=provider.id,
            dynamic_variables=dynamic_vars,
        )

        # Define callbacks to proxy data to frontend
        # Use partial to bind provider.id to avoid loop variable issues
        audio_callback = partial(
            _send_audio_chunk,
            booking_id=booking_id,
            provider_id=provider.id,
        )
        event_callback = partial(
            _send_event,
            booking_id=booking_id,
            provider_id=provider.id,
        )

        # Run conversation
        outcome = "failed"
        try:
            await conversation.start()
            # Register conversation so WebSocket can send user audio to it
            conversation_manager.register(booking_id, conversation)

            outcome = await conversation.listen(audio_callback, event_callback)
            logger.info(
                "Conversation %s completed with outcome: %s",
                conversation_id,
                outcome,
            )
        except ConversationTimeoutError:
            logger.warning("Conversation %s timed out", conversation_id)
            outcome = "timeout"
            # Webhook will update with VOICEMAIL if no answer
        except ConversationConnectionError:
            logger.error("Conversation %s failed to connect", conversation_id)
            outcome = "failed"
            # CallResult already has CALL_FAILED as default
        except Exception:
            logger.exception("Conversation %s failed unexpectedly", conversation_id)
            outcome = "failed"
        finally:
            # Unregister conversation when done
            conversation_manager.unregister(booking_id)

        # Update CallResult end time
        call_result.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        # Notify frontend: conversation ended
        await ws_manager.send_to_booking(
            booking_id,
            {
                "type": "conversation_ended",
                "booking_id": str(booking_id),
                "provider_id": str(provider.id),
                "conversation_id": conversation_id,
                "outcome": outcome,
            },
        )

        logger.info(
            "Finished conversation %s for provider %s",
            conversation_id,
            provider.name,
        )

    logger.info(
        "Completed %d conversations for booking %s",
        len(booking_providers),
        booking_id,
    )
    return call_results


def _build_dynamic_variables(
    booking: Booking,
    user: UserProfile,
    provider: Provider,
) -> dict[str, str]:
    """Build dynamic variables for ElevenLabs agent.

    The agent prompt expects these variables to personalize the conversation.

    Args:
        booking: Booking record
        user: User profile
        provider: Provider to call

    Returns:
        Dictionary of variable name -> value
    """
    return {
        "patient_name": user.name,
        "provider_name": provider.name,
        "service_type": booking.service_type,
        "preferred_date": booking.preferred_date or "flexible",
        "preferred_time": booking.preferred_time or "flexible",
        "patient_phone": user.phone or "not provided",
    }
