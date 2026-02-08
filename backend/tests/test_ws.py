import uuid

import pytest
from starlette.testclient import TestClient

from app.core.websocket_manager import ws_manager
from app.main import app


@pytest.fixture(autouse=True)
def _reset_ws_manager():
    ws_manager._connections.clear()
    yield
    ws_manager._connections.clear()


class TestBookingStatusWebSocket:
    def test_connect_registers_connection(self):
        booking_id = uuid.uuid4()
        client = TestClient(app)

        with client.websocket_connect(f"/ws/bookings/{booking_id}"):
            assert ws_manager.active_connections(booking_id) == 1

        # After disconnect the connection is cleaned up
        assert ws_manager.active_connections(booking_id) == 0

    def test_invalid_booking_id_rejects(self):
        client = TestClient(app)

        with pytest.raises(Exception):  # noqa: B017
            with client.websocket_connect("/ws/bookings/not-a-uuid"):
                pass
