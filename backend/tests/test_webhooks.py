from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_check_calendar_returns_available(client):
    response = await client.post(
        "/api/webhooks/tools/check_calendar",
        json={"date": "2026-02-10", "time": "14:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["conflicts"] == []


@pytest.mark.asyncio
async def test_check_calendar_unavailable(client):
    with patch(
        "app.routers.webhooks.check_user_availability",
        return_value=False,
    ):
        response = await client.post(
            "/api/webhooks/tools/check_calendar",
            json={"date": "2026-02-10", "time": "14:00"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False


@pytest.mark.asyncio
async def test_check_calendar_missing_params(client):
    response = await client.post(
        "/api/webhooks/tools/check_calendar",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_slot_success(client):
    response = await client.post(
        "/api/webhooks/tools/confirm_slot",
        json={"date": "2026-02-10", "time": "14:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["confirmed"] is True
    assert "2026-02-10" in data["message"]
    assert "14:00" in data["message"]


@pytest.mark.asyncio
async def test_confirm_slot_with_notes(client):
    response = await client.post(
        "/api/webhooks/tools/confirm_slot",
        json={
            "date": "2026-02-10",
            "time": "14:00",
            "provider_notes": "Patient prefers morning next time",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["confirmed"] is True


@pytest.mark.asyncio
async def test_confirm_slot_missing_params(client):
    response = await client.post(
        "/api/webhooks/tools/confirm_slot",
        json={"date": "2026-02-10"},
    )
    assert response.status_code == 422


# --- Post-call webhook tests ---


@pytest.mark.asyncio
async def test_post_call_webhook_with_call_result(client):
    mock_cr = MagicMock()
    mock_cr.id = "test-id"
    with patch(
        "app.routers.webhooks.update_call_result_from_webhook",
        new_callable=AsyncMock,
        return_value=mock_cr,
    ):
        response = await client.post(
            "/api/webhooks/elevenlabs/post-call",
            json={
                "conversation_id": "conv-123",
                "data_collection": {
                    "call_outcome": "slot_offered",
                    "available_slot": "February 10th at 14:00",
                    "provider_notes": "Bring ID",
                },
                "analysis": {
                    "slot_secured": True,
                    "stayed_on_topic": True,
                    "professional_tone": True,
                },
                "call_duration_seconds": 120,
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_post_call_webhook_no_call_result(client):
    with patch(
        "app.routers.webhooks.update_call_result_from_webhook",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.post(
            "/api/webhooks/elevenlabs/post-call",
            json={
                "conversation_id": "conv-unknown",
                "data_collection": {},
                "analysis": {},
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_post_call_webhook_missing_conversation_id(client):
    response = await client.post(
        "/api/webhooks/elevenlabs/post-call",
        json={"data_collection": {}},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_call_webhook_minimal_payload(client):
    with patch(
        "app.routers.webhooks.update_call_result_from_webhook",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.post(
            "/api/webhooks/elevenlabs/post-call",
            json={"conversation_id": "conv-456"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
