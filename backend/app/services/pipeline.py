"""Async booking pipeline orchestrator.

Runs the full booking flow in the background after a booking is created:
search -> shortlist -> mock-call -> options_ready.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import async_session
from app.core.websocket_manager import ws_manager
from app.models.booking import Booking, BookingProvider, BookingStatus
from app.models.user import UserProfile
from app.services.booking_service import save_shortlist
from app.services.conversation_orchestrator import run_conversations_for_booking
from app.services.distance_service import calculate_distances
from app.services.mock_calls import generate_mock_call_results
from app.services.provider_search import (
    cache_providers,
    enrich_with_phone,
    search_providers,
)
from app.services.scoring import score_providers

logger = logging.getLogger(__name__)

# Track active pipeline tasks for graceful shutdown.
_active_tasks: set[asyncio.Task[None]] = set()


async def _update_status(
    db: AsyncSession,
    booking_id: uuid.UUID,
    status: BookingStatus,
) -> None:
    """Transition a booking to a new status and broadcast via WebSocket."""
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        msg = f"Booking {booking_id} not found"
        raise ValueError(msg)
    booking.status = status
    await db.commit()
    logger.info("Booking %s → %s", booking_id, status.value)
    await ws_manager.send_to_booking(
        booking_id,
        {"type": "status", "status": status.value, "booking_id": str(booking_id)},
    )


async def _get_user(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Fetch user profile or raise."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        msg = f"User {user_id} not found"
        raise ValueError(msg)
    return user


async def _get_booking_providers(
    db: AsyncSession,
    booking_id: uuid.UUID,
) -> list[BookingProvider]:
    """Fetch persisted BookingProvider records for a booking."""
    result = await db.execute(
        select(BookingProvider).where(
            BookingProvider.booking_id == booking_id
        )
    )
    return list(result.scalars().all())


async def run_booking_pipeline(
    booking_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Orchestrate the full booking pipeline.

    Phases:
        1. Search — find providers via Google Places
        2. Shortlist — calculate distances, score, and persist top providers
        3. Enrich — fetch phone numbers for shortlisted providers only
        4. Call (mock) — simulate calling shortlisted providers
        5. Done — mark booking as ``options_ready``

    On any failure the booking status is set to ``call_failed``.
    """
    try:
        # Load booking and user
        result = await db.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        if booking is None:
            logger.error("Pipeline: booking %s not found", booking_id)
            return

        user = await _get_user(db, booking.user_id)

        # Phase 1: Search providers
        await _update_status(db, booking_id, BookingStatus.SEARCHING)
        providers = await search_providers(
            service_type=booking.service_type,
            lat=user.latitude,
            lng=user.longitude,
            radius_km=user.max_distance_km,
            db=db,
        )

        logger.info(
            "Pipeline: Sending provider_count=%d for booking %s",
            len(providers),
            booking_id,
        )
        await ws_manager.send_to_booking(
            booking_id,
            {
                "type": "provider_count",
                "count": len(providers),
                "booking_id": str(booking_id),
            },
        )

        if not providers:
            logger.warning(
                "Pipeline: no providers found for booking %s", booking_id
            )
            await _update_status(db, booking_id, BookingStatus.CALL_FAILED)
            return

        # Phase 2: Shortlist (scoring works without phone numbers)
        await _update_status(db, booking_id, BookingStatus.SHORTLISTING)
        logger.info("Pipeline: Scoring %d providers for booking %s", len(providers), booking_id)
        distances = await calculate_distances(
            origin=(user.latitude, user.longitude),
            destinations=[(p.latitude, p.longitude) for p in providers],
            mode=user.transport_mode,
        )
        scored = score_providers(
            providers=providers,
            distances=distances,
            blocked_providers=user.blocked_providers,
            preferred_providers=user.preferred_providers,
            min_rating=user.min_rating,
            top_n=user.shortlist_count,
        )

        # Phase 3: Enrich only shortlisted providers with phone numbers
        shortlisted_providers = [s.provider for s in scored]
        needs_phone = [p for p in shortlisted_providers if not p.phone]
        if needs_phone:
            enriched = await enrich_with_phone(needs_phone)
            enriched_map = {p.place_id: p.phone for p in enriched}
            # Update scored entries with enriched phone numbers
            updated_scored = []
            for s in scored:
                phone = enriched_map.get(s.provider.place_id, s.provider.phone)
                if phone:
                    # Provider has phone (either cached or enriched) - update it
                    updated_provider = s.provider.model_copy(update={"phone": phone})
                    updated_scored.append(s.model_copy(update={"provider": updated_provider}))
                else:
                    # Provider has no phone - keep it anyway
                    updated_scored.append(s)
            scored = updated_scored

        logger.info("Pipeline: Saving %d scored providers for booking %s", len(scored), booking_id)
        await save_shortlist(db, booking_id, scored)

        # Cache newly enriched providers for future lookups
        providers_with_phone = [
            s.provider for s in scored if s.provider.phone
        ]
        if providers_with_phone:
            await cache_providers(db, providers_with_phone)

        # Phase 4: Call providers (DEMO MODE - Widget only)
        await _update_status(db, booking_id, BookingStatus.CALLING)

        # DEMO MODE: Pipeline pauses here at CALLING status
        # The frontend ElevenLabs widget will appear and handle the conversation
        # The post-call webhook will create CallResult and transition to OPTIONS_READY

        logger.info(
            "DEMO MODE: Booking %s is now in CALLING status. "
            "Widget conversation will begin, and post-call webhook will complete the phase.",
            booking_id,
        )

        # Send WebSocket event to indicate widget should be shown
        await ws_manager.send_to_booking(
            booking_id,
            {
                "type": "widget_ready",
                "booking_id": str(booking_id),
                "message": "Widget conversation can now begin",
            },
        )

        # Pipeline stops here - will be resumed by post-call webhook
        # DO NOT auto-complete to OPTIONS_READY
        logger.info("Pipeline completed for booking %s", booking_id)

    except Exception:
        logger.exception("Pipeline failed for booking %s", booking_id)
        try:
            # Ensure the session is clean before attempting the status update.
            if db.in_transaction():
                await db.rollback()
            await _update_status(db, booking_id, BookingStatus.CALL_FAILED)
        except Exception:
            logger.exception(
                "Failed to set CALL_FAILED status for booking %s",
                booking_id,
            )


async def _run_pipeline_with_session(booking_id: uuid.UUID) -> None:
    """Run the pipeline with its own database session."""
    async with async_session() as db:
        await run_booking_pipeline(booking_id, db)


def start_pipeline(booking_id: uuid.UUID) -> asyncio.Task[None]:
    """Fire-and-forget the booking pipeline as a background task.

    Creates an ``asyncio.Task`` with its own database session so the
    caller's request session can close independently.

    Args:
        booking_id: The booking to process.

    Returns:
        The background task (for testing / cancellation).
    """
    task = asyncio.create_task(
        _run_pipeline_with_session(booking_id),
        name=f"pipeline-{booking_id}",
    )
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)
    logger.info("Pipeline task started for booking %s", booking_id)
    return task


async def shutdown_pipeline_tasks() -> None:
    """Wait for all active pipeline tasks to finish.

    Call during application shutdown to avoid killing running pipelines.
    """
    if _active_tasks:
        logger.info(
            "Waiting for %d pipeline task(s) to complete",
            len(_active_tasks),
        )
        await asyncio.gather(*_active_tasks, return_exceptions=True)
