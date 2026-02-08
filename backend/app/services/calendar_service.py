"""Google Calendar API service for availability checking and event creation."""

import logging
from datetime import datetime, timedelta, timezone

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

        # Check for errors field in response - fail closed if present
        calendar_data = result.get("calendars", {}).get("primary", {})
        if "errors" in calendar_data:
            logger.warning(
                "Google Calendar API returned errors for user %s: %s",
                user_id,
                calendar_data["errors"],
            )
            return {
                "available": False,
                "calendar_connected": True,
                "conflicts": [],
                "message": "Calendar check failed — assuming busy for safety",
            }

        busy_periods = calendar_data.get("busy", [])

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

    except KeyError as e:
        logger.exception("Malformed response from Google Calendar API: %s", e)
        # Fail closed: assume busy if response is malformed
        return {
            "available": False,
            "calendar_connected": True,
            "conflicts": [],
            "message": "Calendar check failed — assuming busy for safety",
        }
    except Exception:
        logger.exception("Error querying Google Calendar API")
        # Fail closed: assume busy if API fails
        return {
            "available": False,
            "calendar_connected": True,
            "conflicts": [],
            "message": "Calendar check failed — assuming busy for safety",
        }


async def create_calendar_event(
    db: AsyncSession,
    user_id: str,
    provider_name: str,
    provider_address: str,
    slot: datetime,
    service_type: str,
    booking_id: str | None = None,
) -> dict | None:
    """Create a calendar event for a confirmed booking.

    Args:
        db: Database session.
        user_id: User UUID.
        provider_name: Name of the provider.
        provider_address: Address of the provider.
        slot: The appointment datetime.
        service_type: Type of service booked.
        booking_id: Optional booking ID to include in description.

    Returns:
        Dict with event_id and event_link if successful, None if calendar
        not connected or API fails.
    """
    credentials = await get_calendar_credentials(db, user_id)
    if not credentials:
        logger.info(
            "User %s has not connected their calendar, skipping event creation",
            user_id,
        )
        return None

    try:
        service = build("calendar", "v3", credentials=credentials)

        # Ensure slot is timezone-aware (database stores as naive UTC)
        if slot.tzinfo is None:
            slot_utc = slot.replace(tzinfo=timezone.utc)
        else:
            slot_utc = slot.astimezone(timezone.utc)

        # Calculate 1-hour duration
        end_time_utc = slot_utc + timedelta(hours=1)

        # Build event body
        event_body = {
            "summary": f"{service_type} - {provider_name}",
            "location": provider_address,
            "description": f"Appointment with {provider_name} for {service_type}"
            + (f"\nBooking ID: {booking_id}" if booking_id else ""),
            "start": {
                "dateTime": slot_utc.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time_utc.isoformat(),
                "timeZone": "UTC",
            },
        }

        logger.info(
            "Creating calendar event for %s at %s",
            provider_name,
            slot_utc.isoformat(),
        )
        event = service.events().insert(
            calendarId="primary", body=event_body
        ).execute()

        event_id = event.get("id")
        event_link = event.get("htmlLink")

        logger.info(
            "Calendar event created successfully: %s (%s)",
            event_id,
            event_link,
        )

        return {
            "event_id": event_id,
            "event_link": event_link,
        }

    except Exception:
        logger.exception("Error creating calendar event")
        return None
