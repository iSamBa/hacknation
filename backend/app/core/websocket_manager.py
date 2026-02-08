"""WebSocket connection manager for real-time booking status updates."""

import logging
import uuid
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by booking ID."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, booking_id: uuid.UUID) -> None:
        """Accept and register a WebSocket connection for a booking."""
        await websocket.accept()
        self._connections[booking_id].append(websocket)
        logger.info(
            "WebSocket connected for booking %s (%d active)",
            booking_id,
            len(self._connections[booking_id]),
        )

    def disconnect(self, websocket: WebSocket, booking_id: uuid.UUID) -> None:
        """Remove a WebSocket connection."""
        conns = self._connections[booking_id]
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            del self._connections[booking_id]
        logger.info("WebSocket disconnected for booking %s", booking_id)

    async def send_to_booking(
        self,
        booking_id: uuid.UUID,
        message: dict,
    ) -> None:
        """Send a JSON message to all connections watching a booking."""
        conns = list(self._connections.get(booking_id, []))
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning(
                    "Failed to send to WebSocket for booking %s, removing",
                    booking_id,
                )
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws, booking_id)

    def active_connections(self, booking_id: uuid.UUID) -> int:
        """Return the number of active connections for a booking."""
        return len(self._connections.get(booking_id, []))


ws_manager = ConnectionManager()
