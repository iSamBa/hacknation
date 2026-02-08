"""Async booking pipeline orchestrator.

Runs the full booking flow in the background after a booking is created:
search -> shortlist -> mock-call -> options_ready.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.booking import Booking, BookingProvider, BookingStatus
from app.models.user import UserProfile
from app.services.booking_service import save_shortlist
from app.services.distance_service import calculate_distances
from app.services.mock_calls import generate_mock_call_results
from app.services.provider_search import search_providers
from app.services.scoring import score_providers

logger = logging.getLogger(__name__)

# Track active pipeline tasks for graceful shutdown.
_active_tasks: set[asyncio.Task[None]] = set()


async def _update_status(
    db: AsyncSession,
    booking_id: uuid.UUID,
    status: BookingStatus,
) -> None:
    """Transition a booking to a new status."""
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
        3. Call (mock) — simulate calling shortlisted providers
        4. Done — mark booking as ``options_ready``

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

        if not providers:
            logger.warning(
                "Pipeline: no providers found for booking %s", booking_id
            )
            await _update_status(db, booking_id, BookingStatus.CALL_FAILED)
            return

        # Phase 2: Shortlist
        await _update_status(db, booking_id, BookingStatus.SHORTLISTING)
        distances = await calculate_distances(
            origin=(user.latitude, user.longitude),
            destinations=[(p.latitude, p.longitude) for p in providers],
        )
        scored = score_providers(
            providers=providers,
            distances=distances,
            blocked_providers=user.blocked_providers,
            preferred_providers=user.preferred_providers,
            min_rating=user.min_rating,
        )
        await save_shortlist(db, booking_id, scored)

        # Phase 3: Call (mocked)
        await _update_status(db, booking_id, BookingStatus.CALLING)
        booking_providers = await _get_booking_providers(db, booking_id)
        await generate_mock_call_results(db, booking_id, booking_providers)

        # Phase 4: Done
        await _update_status(db, booking_id, BookingStatus.OPTIONS_READY)
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
