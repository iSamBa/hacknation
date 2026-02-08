import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.post_call_handler import (
    update_call_result_from_webhook,
)

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
async def confirm_slot(body: ConfirmSlotRequest):
    """Confirm and record the agreed appointment slot.

    Called by the ElevenLabs agent as a server tool during
    a live conversation.
    """
    logger.info(
        "Slot confirmed: %s at %s (notes: %s)",
        body.date, body.time, body.provider_notes,
    )
    return ConfirmSlotResponse(
        confirmed=True,
        message=f"Slot confirmed for {body.date} at {body.time}",
    )


@router.post(
    "/elevenlabs/post-call",
    response_model=PostCallWebhookResponse,
)
async def post_call_webhook(
    body: PostCallWebhookRequest, db: DbSession,
):
    """Receive post-call data from ElevenLabs.

    Processes data collection results and analysis criteria
    from a completed call, updating the corresponding
    CallResult record.
    """
    await update_call_result_from_webhook(
        db,
        conversation_id=body.conversation_id,
        data_collection=body.data_collection,
        analysis=body.analysis,
        transcript=body.transcript,
        call_duration_seconds=body.call_duration_seconds,
    )
    return PostCallWebhookResponse(status="ok")
