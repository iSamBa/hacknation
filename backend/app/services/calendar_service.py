"""Google Calendar API service for availability checking and event creation."""

import logging
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.encryption import decrypt_token, encrypt_token
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)


async def get_oauth_token(
    db: AsyncSession, user_id: str, provider: str = "google"
) -> OAuthToken | None:
    """Retrieve OAuth token for a user and provider.

    Args:
        db: Database session.
        user_id: User UUID.
        provider: OAuth provider name (default: "google").

    Returns:
        OAuthToken if found, None otherwise.
    """
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id, OAuthToken.provider == provider
        )
    )
    return result.scalar_one_or_none()


async def get_calendar_credentials(
    db: AsyncSession, user_id: str
) -> Credentials | None:
    """Load and refresh Google Calendar credentials for a user.

    Args:
        db: Database session.
        user_id: User UUID.

    Returns:
        Credentials if token exists and is valid, None if user hasn't
        connected calendar.

    Raises:
        ValueError: If GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        msg = "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured"
        raise ValueError(msg)

    token = await get_oauth_token(db, user_id, provider="google")
    if not token:
        return None

    credentials = Credentials(
        token=decrypt_token(token.access_token),
        refresh_token=decrypt_token(token.refresh_token),
        token_uri="https://oauth2.googleapis.com/token",  # noqa: S106
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=token.scopes,
    )

    # Refresh if expired
    if credentials.expired:
        logger.info("Access token expired, refreshing for user %s", user_id)
        credentials.refresh(Request())
        # Update stored tokens
        token.access_token = encrypt_token(credentials.token)
        token.token_expiry = credentials.expiry
        await db.commit()
        logger.info("Access token refreshed successfully")

    return credentials


async def check_availability(
    db: AsyncSession, user_id: str, start: datetime, end: datetime
) -> dict:
    """Check if the user is free during the given time range.

    Queries Google Calendar FreeBusy API to check for conflicts.

    Args:
        db: Database session.
        user_id: User UUID.
        start: Start of time range to check.
        end: End of time range to check.

    Returns:
        Dictionary with:
        - available (bool): True if no conflicts found.
        - calendar_connected (bool): True if user has connected their calendar.
        - conflicts (list[dict]): List of conflict time ranges.
        - message (str, optional): Additional context message.
    """
    credentials = await get_calendar_credentials(db, user_id)
    if not credentials:
        logger.info("User %s has not connected their calendar", user_id)
        return {
            "available": True,
            "calendar_connected": False,
            "conflicts": [],
            "message": "Calendar not connected — assuming available",
        }

    try:
        service = build("calendar", "v3", credentials=credentials)

        # Convert to UTC ISO format for Google API
        time_min = start.astimezone(timezone.utc).isoformat()
        time_max = end.astimezone(timezone.utc).isoformat()

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": "primary"}],
        }

        logger.info("Querying FreeBusy API for %s to %s", time_min, time_max)
        result = service.freebusy().query(body=body).execute()
        busy_periods = result["calendars"]["primary"]["busy"]

        conflicts = [
            {"start": period["start"], "end": period["end"]}
            for period in busy_periods
        ]

        available = len(busy_periods) == 0
        logger.info(
            "Availability check: available=%s, conflicts=%d",
            available,
            len(conflicts),
        )

        return {
            "available": available,
            "calendar_connected": True,
            "conflicts": conflicts,
        }

    except Exception:
        logger.exception("Error querying Google Calendar API")
        # Graceful degradation: assume available if API fails
        return {
            "available": True,
            "calendar_connected": True,
            "conflicts": [],
            "message": "Calendar check failed — assuming available",
        }


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
