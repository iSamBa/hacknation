"""Google Calendar event creation (stub for MVP).

Actual Google Calendar OAuth integration is out of scope.
This module logs the event details that would be created.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def create_calendar_event(
    user_name: str,
    provider_name: str,
    provider_address: str,
    slot: datetime,
    service_type: str,
) -> dict:
    """Create a calendar event for a confirmed booking.

    For MVP, this is a stub that logs the event and returns
    the event details that would be sent to Google Calendar.

    Args:
        user_name: Name of the user.
        provider_name: Name of the provider.
        provider_address: Address of the provider.
        slot: The appointment datetime.
        service_type: Type of service booked.

    Returns:
        Dict with event details (stub).
    """
    event = {
        "summary": f"{service_type} - {provider_name}",
        "location": provider_address,
        "start": slot.isoformat(),
        "description": f"Appointment with {provider_name} for {service_type}",
    }

    logger.info(
        "Calendar event stub: %s at %s on %s",
        provider_name,
        provider_address,
        slot.isoformat(),
    )

    return event
