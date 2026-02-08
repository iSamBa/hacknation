import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.websocket_manager import ConnectionManager


def _make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_accepts_and_registers(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        booking_id = uuid.uuid4()

        await mgr.connect(ws, booking_id)

        ws.accept.assert_awaited_once()
        assert mgr.active_connections(booking_id) == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        booking_id = uuid.uuid4()

        await mgr.connect(ws, booking_id)
        mgr.disconnect(ws, booking_id)

        assert mgr.active_connections(booking_id) == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_does_not_raise(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        booking_id = uuid.uuid4()

        # Should not raise
        mgr.disconnect(ws, booking_id)

    @pytest.mark.asyncio
    async def test_send_to_booking_sends_json(self):
        mgr = ConnectionManager()
        ws = _make_ws()
        booking_id = uuid.uuid4()
        message = {"type": "status", "status": "searching"}

        await mgr.connect(ws, booking_id)
        await mgr.send_to_booking(booking_id, message)

        ws.send_json.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_booking_multiple_clients(self):
        mgr = ConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        booking_id = uuid.uuid4()
        message = {"type": "status", "status": "shortlisting"}

        await mgr.connect(ws1, booking_id)
        await mgr.connect(ws2, booking_id)

        assert mgr.active_connections(booking_id) == 2

        await mgr.send_to_booking(booking_id, message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_booking_removes_stale_connections(self):
        mgr = ConnectionManager()
        healthy_ws = _make_ws()
        stale_ws = _make_ws()
        stale_ws.send_json.side_effect = RuntimeError("connection closed")
        booking_id = uuid.uuid4()

        await mgr.connect(healthy_ws, booking_id)
        await mgr.connect(stale_ws, booking_id)
        assert mgr.active_connections(booking_id) == 2

        await mgr.send_to_booking(booking_id, {"type": "status"})

        # Stale connection should have been removed
        assert mgr.active_connections(booking_id) == 1
        healthy_ws.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_to_booking_no_connections(self):
        mgr = ConnectionManager()
        booking_id = uuid.uuid4()

        # Should not raise
        await mgr.send_to_booking(booking_id, {"type": "status"})

    @pytest.mark.asyncio
    async def test_multiple_bookings_isolated(self):
        mgr = ConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        booking1 = uuid.uuid4()
        booking2 = uuid.uuid4()

        await mgr.connect(ws1, booking1)
        await mgr.connect(ws2, booking2)

        msg = {"type": "status", "status": "searching"}
        await mgr.send_to_booking(booking1, msg)

        ws1.send_json.assert_awaited_once_with(msg)
        ws2.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_active_connections_returns_zero_for_unknown(self):
        mgr = ConnectionManager()
        assert mgr.active_connections(uuid.uuid4()) == 0
