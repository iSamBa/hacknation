"""Tests for Google OAuth authentication router."""

from unittest.mock import patch

from app.routers.auth import _oauth_states


async def test_authorize_returns_url_and_state(client):
    """GET /authorize should return authorization URL and state."""
    with (
        patch("app.routers.auth.build_auth_flow") as mock_build_flow,
        patch("app.routers.auth.get_authorization_url") as mock_get_url,
    ):
        mock_get_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?...",
            "state-123",
        )

        response = await client.get("/api/auth/google/authorize")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["state"] == "state-123"
        assert data["authorization_url"].startswith("https://accounts.google.com")
        # State should be stored for CSRF validation
        assert "state-123" in _oauth_states


async def test_callback_with_invalid_state_returns_400(client):
    """GET /callback with invalid state should return 400."""
    response = await client.get(
        "/api/auth/google/callback",
        params={"code": "auth-code", "state": "invalid-state"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid or expired state" in data["detail"]


async def test_callback_exchange_failure_returns_400(client):
    """GET /callback should return 400 if token exchange fails."""
    _oauth_states["state-fail"] = "pending"

    with (
        patch("app.routers.auth.build_auth_flow"),
        patch(
            "app.routers.auth.exchange_code_for_tokens",
            side_effect=Exception("Token exchange failed"),
        ),
    ):
        response = await client.get(
            "/api/auth/google/callback",
            params={"code": "bad-code", "state": "state-fail"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Token exchange failed" in data["detail"]
