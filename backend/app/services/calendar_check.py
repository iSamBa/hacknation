"""Calendar availability checking service.

This module provides the high-level availability checking function
that integrates with Google Calendar via calendar_service.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

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
    start = datetime.fromisoformat(f"{date}T{time}")
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
