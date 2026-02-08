"""WebSocket endpoint for real-time booking status updates."""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.conversation_manager import conversation_manager
from app.core.database import async_session
from app.core.websocket_manager import ws_manager
from app.services.booking_service import get_booking

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/bookings/{booking_id}")
async def booking_status_ws(websocket: WebSocket, booking_id: uuid.UUID):
    """Stream real-time status updates for a booking.

    Clients connect and receive JSON messages as the booking pipeline
    progresses through its phases.
    """
    await ws_manager.connect(websocket, booking_id)

    # Send current state so the client catches up with any missed updates
    try:
        async with async_session() as db:
            booking = await get_booking(db, booking_id)
            if booking:
                status_val = (
                    booking.status.value
                    if hasattr(booking.status, "value")
                    else booking.status
                )
                await websocket.send_json({
                    "type": "status",
                    "status": status_val,
                    "booking_id": str(booking_id),
                })
                # Note: provider_count is sent by the pipeline after search phase.
                # Do NOT send it here as it would show booking_providers count
                # (shortlist) instead of the actual search results count.
    except Exception:
        logger.exception("Failed to send initial state for booking %s", booking_id)

    try:
        while True:
            # Receive messages from frontend
            message = await websocket.receive_text()

            try:
                data = json.loads(message)
                msg_type = data.get("type")

                # Handle user audio input
                if msg_type == "user_audio":
                    conversation = conversation_manager.get(booking_id)
                    if conversation:
                        # Get base64 audio from frontend
                        audio_base64 = data.get("audio")
                        if audio_base64:
                            # Forward base64 audio directly to ElevenLabs
                            await conversation.send_user_audio(audio_base64)
                            logger.debug("Forwarded user audio to ElevenLabs")
                    else:
                        logger.warning(
                            "No active conversation for booking %s, cannot send audio",
                            booking_id,
                        )

            except json.JSONDecodeError:
                logger.warning("Received invalid JSON from websocket")
            except Exception:
                logger.exception("Error processing websocket message")

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for booking %s", booking_id)
    finally:
        ws_manager.disconnect(websocket, booking_id)
