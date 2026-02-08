"""Google OAuth2 authentication service."""

import logging

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def build_auth_flow(redirect_uri: str) -> Flow:
    """Create OAuth2 flow with client credentials.

    Args:
        redirect_uri: The OAuth callback URL where Google will redirect after consent.

    Returns:
        Configured Flow instance for OAuth2 authorization.

    Raises:
        ValueError: If GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        msg = "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured"
        raise ValueError(msg)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


def get_authorization_url(flow: Flow) -> tuple[str, str]:
    """Generate authorization URL and state for CSRF protection.

    Args:
        flow: The OAuth2 flow instance.

    Returns:
        Tuple of (authorization_url, state_token).
    """
    url, state = flow.authorization_url(
        access_type="offline",  # get refresh token
        include_granted_scopes="true",
        prompt="consent",  # force consent to always get refresh token
    )
    return url, state


def exchange_code_for_tokens(flow: Flow, code: str) -> dict:
    """Exchange authorization code for access and refresh tokens.

    Args:
        flow: The OAuth2 flow instance.
        code: The authorization code from Google callback.

    Returns:
        Dictionary containing access_token, refresh_token, token_expiry, and scopes.
    """
    flow.fetch_token(code=code)
    credentials = flow.credentials
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": credentials.expiry,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
    }


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token using a refresh token.

    Args:
        refresh_token: The refresh token to use.

    Returns:
        Dictionary containing new access_token and token_expiry.

    Raises:
        ValueError: If GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        msg = "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured"
        raise ValueError(msg)

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",  # noqa: S106
    )
    credentials.refresh(Request())
    return {
        "access_token": credentials.token,
        "token_expiry": credentials.expiry,
    }


async def revoke_token(access_token: str) -> bool:
    """Revoke the OAuth token at Google.

    Args:
        access_token: The access token to revoke.

    Returns:
        True if revocation successful, False otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": access_token},
                timeout=10.0,
            )
            return resp.status_code == 200
    except Exception:
        logger.exception("Failed to revoke token at Google")
        return False
