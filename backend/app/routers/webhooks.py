import hashlib
import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_db
from app.schemas.webhook import (
    CheckCalendarRequest,
    CheckCalendarResponse,
    ConfirmSlotRequest,
    ConfirmSlotResponse,
    PostCallWebhookRequest,
    PostCallWebhookResponse,
)
from app.services.calendar_check import check_user_availability
from app.services.calendar_service import create_calendar_event
from app.services.post_call_handler import (
    update_call_result_from_webhook,
)
from app.services.user_service import get_or_create_default_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/tools/check_calendar",
    response_model=CheckCalendarResponse,
)
async def check_calendar(body: CheckCalendarRequest, db: DbSession):
    """Check if the patient is available at the proposed date and time.

    Called by the ElevenLabs agent as a server tool during
    a live conversation.
    """
    result = await check_user_availability(db, body.date, body.time)

    # Format conflicts as strings for the response
    conflicts = [
        f"{c['start']} to {c['end']}" for c in result.get("conflicts", [])
    ]

    return CheckCalendarResponse(
        available=result["available"], conflicts=conflicts
    )


@router.post(
    "/tools/confirm_slot",
    response_model=ConfirmSlotResponse,
)
async def confirm_slot(body: ConfirmSlotRequest, db: DbSession):
    """Confirm and record the agreed appointment slot.

    Called by the ElevenLabs agent as a server tool during
    a live conversation. Creates a calendar event if provider
    information is provided.
    """
    logger.info(
        "Slot confirmed: %s at %s (provider: %s, notes: %s)",
        body.date, body.time, body.provider_name, body.provider_notes,
    )

    # Create calendar event if we have the necessary information
    if body.provider_name and body.service_type:
        from zoneinfo import ZoneInfo

        from dateutil import parser as dateutil_parser

        from app.config import settings

        # Parse date and time into datetime (same logic as calendar_check)
        naive_start = dateutil_parser.parse(f"{body.date} {body.time}", fuzzy=True)
        tz = ZoneInfo(settings.DEFAULT_TIMEZONE)
        slot = naive_start.replace(tzinfo=tz)

        # Get the default user
        user = await get_or_create_default_user(db)

        try:
            event_result = await create_calendar_event(
                db=db,
                user_id=str(user.id),
                provider_name=body.provider_name,
                provider_address=body.provider_address or "Address not provided",
                slot=slot,
                service_type=body.service_type,
            )
            if event_result:
                logger.info(
                    "Calendar event created for slot %s at %s: %s",
                    body.date,
                    body.time,
                    event_result.get("event_link"),
                )
                return ConfirmSlotResponse(
                    confirmed=True,
                    message=(
                        f"Slot confirmed and added to your calendar "
                        f"for {body.date} at {body.time}"
                    ),
                )
            else:
                logger.warning(
                    "Calendar event not created (calendar not connected or failed)"
                )
        except Exception:
            logger.exception("Failed to create calendar event")

    return ConfirmSlotResponse(
        confirmed=True,
        message=f"Slot confirmed for {body.date} at {body.time}",
    )


def verify_elevenlabs_signature(
    payload: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    """Verify ElevenLabs HMAC signature.

    Args:
        payload: Raw request body bytes
        signature: Signature from x-elevenlabs-signature header
        secret: Webhook secret from ElevenLabs

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@router.post(
    "/elevenlabs/post-call",
    response_model=PostCallWebhookResponse,
)
async def post_call_webhook(
    request: Request,
    body: PostCallWebhookRequest,
    db: DbSession,
    x_elevenlabs_signature: str | None = Header(None),
):
    """Receive post-call data from ElevenLabs.

    Processes data collection results and analysis criteria
    from a completed call, updating the corresponding
    CallResult record.

    Verifies HMAC signature for security.
    """
    # Verify signature if secret is configured
    if settings.ELEVENLABS_WEBHOOK_SECRET:
        raw_body = await request.body()
        if not verify_elevenlabs_signature(
            raw_body,
            x_elevenlabs_signature,
            settings.ELEVENLABS_WEBHOOK_SECRET,
        ):
            logger.warning(
                "Invalid ElevenLabs webhook signature for conversation %s",
                body.conversation_id,
            )
            raise HTTPException(status_code=401, detail="Invalid signature")

    await update_call_result_from_webhook(
        db,
        conversation_id=body.conversation_id,
        data_collection=body.data_collection,
        analysis=body.analysis,
        transcript=body.transcript,
        call_duration_seconds=body.call_duration_seconds,
    )
    return PostCallWebhookResponse(status="ok")
