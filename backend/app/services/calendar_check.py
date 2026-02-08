"""Calendar availability checking service.

This module provides the high-level availability checking function
that integrates with Google Calendar via calendar_service.
"""

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from dateutil import parser as dateutil_parser
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.calendar_service import check_availability
from app.services.user_service import get_or_create_default_user

logger = logging.getLogger(__name__)


async def check_user_availability(
    db: AsyncSession, date: str, time: str
) -> dict:
    """Check user availability using real Google Calendar integration.

    Args:
        db: Database session.
        date: Date in ISO format (YYYY-MM-DD).
        time: Time in HH:MM format (24-hour).

    Returns:
        Dictionary with:
        - available (bool): True if no conflicts found.
        - calendar_connected (bool): True if user has connected their calendar.
        - conflicts (list[dict]): List of conflict time ranges.
        - message (str, optional): Additional context message.
    """
    # Parse date and time into datetime range (assume 1-hour slot)
    # The ElevenLabs agent may send natural language ("February 9th", "2 PM")
    # or ISO format ("2026-02-09", "14:00"), so use fuzzy parsing.
    # IMPORTANT: Make the datetime timezone-aware using the user's timezone
    # to ensure correct comparison with Google Calendar events.
    naive_start = dateutil_parser.parse(f"{date} {time}", fuzzy=True)
    tz = ZoneInfo(settings.DEFAULT_TIMEZONE)
    start = naive_start.replace(tzinfo=tz)
    end = start + timedelta(hours=1)

    # For MVP: use the single default user's ID
    user = await get_or_create_default_user(db)

    logger.info(
        "Checking availability for user %s: %s at %s",
        user.id,
        date,
        time,
    )

    result = await check_availability(db, str(user.id), start, end)
    return result
