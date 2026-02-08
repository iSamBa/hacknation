import logging

from fastapi import APIRouter

from app.schemas.webhook import (
    CheckCalendarRequest,
    CheckCalendarResponse,
    ConfirmSlotRequest,
    ConfirmSlotResponse,
)
from app.services.calendar_check import check_user_availability

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/tools", tags=["webhooks"])


@router.post("/check_calendar", response_model=CheckCalendarResponse)
async def check_calendar(body: CheckCalendarRequest):
    """Check if the patient is available at the proposed date and time.

    Called by the ElevenLabs agent as a server tool during a live conversation.
    """
    available = await check_user_availability(body.date, body.time)
    return CheckCalendarResponse(available=available, conflicts=[])


@router.post("/confirm_slot", response_model=ConfirmSlotResponse)
async def confirm_slot(body: ConfirmSlotRequest):
    """Confirm and record the agreed appointment slot.

    Called by the ElevenLabs agent as a server tool during a live conversation.
    For MVP, this returns a confirmation message without persisting to DB
    (CallResult is updated post-call via Story 003).
    """
    logger.info(
        "Slot confirmed: %s at %s (notes: %s)",
        body.date, body.time, body.provider_notes,
    )
    return ConfirmSlotResponse(
        confirmed=True,
        message=f"Slot confirmed for {body.date} at {body.time}",
    )
