from unittest.mock import patch

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
