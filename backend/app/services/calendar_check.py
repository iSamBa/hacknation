import logging

logger = logging.getLogger(__name__)


async def check_user_availability(date: str, time: str) -> bool:
    """Check if the user is free at the proposed date and time.

    For MVP, this is a stub that always returns True.
    Later: integrate with Google Calendar API.
    """
    logger.info(
        "Checking availability for %s at %s (stub)", date, time,
    )
    return True
