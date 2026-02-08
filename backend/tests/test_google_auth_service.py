"""Tests for Google OAuth authentication service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from google_auth_oauthlib.flow import Flow

from app.services.google_auth import (
    SCOPES,
    build_auth_flow,
    exchange_code_for_tokens,
    get_authorization_url,
    refresh_access_token,
    revoke_token,
)


class TestBuildAuthFlow:
    def test_creates_flow_with_correct_config(self):
        """build_auth_flow should create Flow with Google credentials."""
        with patch("app.services.google_auth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"

            flow = build_auth_flow("http://localhost/callback")

            assert isinstance(flow, Flow)
            assert flow.redirect_uri == "http://localhost/callback"

    def test_raises_error_if_credentials_missing(self):
        """build_auth_flow should raise ValueError if credentials not configured."""
        with patch("app.services.google_auth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = None
            mock_settings.GOOGLE_CLIENT_SECRET = None

            with pytest.raises(ValueError, match="must be configured"):
                build_auth_flow("http://localhost/callback")


class TestGetAuthorizationUrl:
    def test_returns_url_and_state(self):
        """get_authorization_url should return tuple of (url, state)."""
        mock_flow = MagicMock(spec=Flow)
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?...",
            "random-state-123",
        )

        url, state = get_authorization_url(mock_flow)

        assert url.startswith("https://accounts.google.com")
        assert state == "random-state-123"
        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )


class TestExchangeCodeForTokens:
    def test_exchanges_code_and_returns_tokens(self):
        """exchange_code_for_tokens should fetch tokens and return dict."""
        mock_flow = MagicMock(spec=Flow)
        mock_credentials = Mock()
        mock_credentials.token = "access-token-123"
        mock_credentials.refresh_token = "refresh-token-456"
        mock_credentials.expiry = datetime(2026, 12, 31, tzinfo=timezone.utc)
        mock_credentials.scopes = SCOPES
        mock_flow.credentials = mock_credentials

        result = exchange_code_for_tokens(mock_flow, "auth-code-789")

        assert result["access_token"] == "access-token-123"
        assert result["refresh_token"] == "refresh-token-456"
        assert result["token_expiry"] == datetime(2026, 12, 31, tzinfo=timezone.utc)
        assert result["scopes"] == SCOPES
        mock_flow.fetch_token.assert_called_once_with(code="auth-code-789")

    def test_handles_none_scopes(self):
        """exchange_code_for_tokens should use default SCOPES if credentials.scopes is None."""
        mock_flow = MagicMock(spec=Flow)
        mock_credentials = Mock()
        mock_credentials.token = "access-token"
        mock_credentials.refresh_token = "refresh-token"
        mock_credentials.expiry = datetime(2026, 12, 31, tzinfo=timezone.utc)
        mock_credentials.scopes = None
        mock_flow.credentials = mock_credentials

        result = exchange_code_for_tokens(mock_flow, "code")

        assert result["scopes"] == SCOPES


class TestRefreshAccessToken:
    def test_refreshes_token_successfully(self):
        """refresh_access_token should refresh credentials and return new token."""
        with (
            patch("app.services.google_auth.settings") as mock_settings,
            patch("app.services.google_auth.Credentials") as mock_creds_class,
            patch("app.services.google_auth.Request") as mock_request,
        ):
            mock_settings.GOOGLE_CLIENT_ID = "client-id"
            mock_settings.GOOGLE_CLIENT_SECRET = "client-secret"

            mock_creds = Mock()
            mock_creds.token = "new-access-token"
            mock_creds.expiry = datetime(2027, 1, 1, tzinfo=timezone.utc)
            mock_creds_class.return_value = mock_creds

            result = refresh_access_token("old-refresh-token")

            assert result["access_token"] == "new-access-token"
            assert result["token_expiry"] == datetime(2027, 1, 1, tzinfo=timezone.utc)
            mock_creds.refresh.assert_called_once()

    def test_raises_error_if_credentials_missing(self):
        """refresh_access_token should raise ValueError if credentials not configured."""
        with patch("app.services.google_auth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = None
            mock_settings.GOOGLE_CLIENT_SECRET = None

            with pytest.raises(ValueError, match="must be configured"):
                refresh_access_token("refresh-token")


class TestRevokeToken:
    async def test_revokes_token_successfully(self):
        """revoke_token should call Google revocation endpoint and return True."""
        with patch("app.services.google_auth.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 200
            # Mock the async post method with AsyncMock
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await revoke_token("access-token")

            assert result is True
            mock_client.post.assert_awaited_once_with(
                "https://oauth2.googleapis.com/revoke",
                params={"token": "access-token"},
                timeout=10.0,
            )

    async def test_returns_false_on_non_200_response(self):
        """revoke_token should return False if Google returns non-200 status."""
        with patch("app.services.google_auth.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = Mock()
            mock_response.status_code = 400
            # Mock the async post method with AsyncMock
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await revoke_token("access-token")

            assert result is False

    async def test_returns_false_on_exception(self):
        """revoke_token should return False and log error if exception occurs."""
        with patch("app.services.google_auth.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            # Mock the async post method to raise exception
            mock_client.post = AsyncMock(side_effect=Exception("Network error"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await revoke_token("access-token")

            assert result is False
