"""WebSocket endpoint for real-time booking status updates."""

import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/bookings/{booking_id}")
async def booking_status_ws(websocket: WebSocket, booking_id: uuid.UUID):
    """Stream real-time status updates for a booking.

    Clients connect and receive JSON messages as the booking pipeline
    progresses through its phases.
    """
    await ws_manager.connect(websocket, booking_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for booking %s", booking_id)
    finally:
        ws_manager.disconnect(websocket, booking_id)
