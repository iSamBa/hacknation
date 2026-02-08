"""Google OAuth2 authentication endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_db
from app.core.encryption import decrypt_token, encrypt_token
from app.models.oauth_token import OAuthToken
from app.schemas.auth import GoogleAuthorizeResponse, GoogleAuthStatusResponse
from app.services.google_auth import (
    build_auth_flow,
    exchange_code_for_tokens,
    get_authorization_url,
    revoke_token,
)
from app.services.user_service import get_or_create_default_user

router = APIRouter(prefix="/api/auth/google", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

logger = logging.getLogger(__name__)

# In-memory state storage for CSRF protection (MVP: single user)
# Production: use secure session storage or encrypted cookies
_oauth_states: dict[str, str] = {}


@router.get("/authorize", response_model=GoogleAuthorizeResponse)
async def authorize(response: Response):
    """Start OAuth2 flow — returns Google consent URL with state parameter.

    Returns:
        JSON with authorization_url and state (for CSRF verification).
    """
    redirect_uri = f"{settings.BACKEND_URL}/api/auth/google/callback"
    flow = build_auth_flow(redirect_uri)
    url, state = get_authorization_url(flow)

    # Store state for CSRF protection (expires after use)
    _oauth_states[state] = "pending"

    return GoogleAuthorizeResponse(authorization_url=url, state=state)


@router.get("/callback")
async def callback(code: str, state: str, db: DbSession):
    """Handle OAuth2 callback — exchange code for tokens and store.

    Args:
        code: Authorization code from Google.
        state: State parameter for CSRF protection.
        db: Database session.

    Returns:
        Redirect to frontend preferences page with status.
    """
    # Validate state (CSRF protection)
    if state not in _oauth_states:
        raise HTTPException(
            status_code=400, detail="Invalid or expired state parameter"
        )

    # Remove state after verification (single use)
    _oauth_states.pop(state, None)

    # Exchange code for tokens
    redirect_uri = f"{settings.BACKEND_URL}/api/auth/google/callback"
    flow = build_auth_flow(redirect_uri)

    try:
        tokens = exchange_code_for_tokens(flow, code)
    except Exception as e:
        logger.exception("Failed to exchange authorization code")
        raise HTTPException(
            status_code=400, detail=f"Token exchange failed: {e!s}"
        ) from e

    # Get or create default user
    user = await get_or_create_default_user(db)

    # Encrypt tokens before storage
    encrypted_access = encrypt_token(tokens["access_token"])
    encrypted_refresh = encrypt_token(tokens["refresh_token"])

    # Check if token already exists for this user/provider
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id, OAuthToken.provider == "google"
        )
    )
    existing_token = result.scalar_one_or_none()

    if existing_token:
        # Update existing token
        existing_token.access_token = encrypted_access
        existing_token.refresh_token = encrypted_refresh
        existing_token.token_expiry = tokens["token_expiry"]
        existing_token.scopes = tokens["scopes"]
    else:
        # Create new token
        oauth_token = OAuthToken(
            user_id=user.id,
            provider="google",
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            token_expiry=tokens["token_expiry"],
            scopes=tokens["scopes"],
        )
        db.add(oauth_token)

    # Handle race condition where another callback created the token
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Token was created by concurrent callback, fetch and update it
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user.id, OAuthToken.provider == "google"
            )
        )
        existing_token = result.scalar_one()
        existing_token.access_token = encrypted_access
        existing_token.refresh_token = encrypted_refresh
        existing_token.token_expiry = tokens["token_expiry"]
        existing_token.scopes = tokens["scopes"]
        await db.commit()

    # Redirect to frontend with success status
    redirect_url = f"{settings.FRONTEND_URL}/preferences?calendar=connected"
    return RedirectResponse(url=redirect_url)


@router.get("/status", response_model=GoogleAuthStatusResponse)
async def status(db: DbSession):
    """Check if user has connected Google Calendar.

    Returns:
        JSON with connected status and scopes.
    """
    user = await get_or_create_default_user(db)

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id, OAuthToken.provider == "google"
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        return GoogleAuthStatusResponse(connected=False, scopes=[])

    return GoogleAuthStatusResponse(connected=True, scopes=token.scopes)


@router.post("/disconnect")
async def disconnect(db: DbSession):
    """Revoke and delete Google Calendar tokens.

    Returns:
        JSON with disconnected status.
    """
    user = await get_or_create_default_user(db)

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id, OAuthToken.provider == "google"
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        return {"disconnected": True, "message": "No token found"}

    # Decrypt access token and revoke at Google
    try:
        access_token = decrypt_token(token.access_token)
        revoked = await revoke_token(access_token)
        if not revoked:
            logger.warning("Failed to revoke token at Google, but deleting locally")
    except Exception:
        logger.exception("Error during token revocation")

    # Delete token from database
    await db.delete(token)
    await db.commit()

    return {"disconnected": True, "message": "Token revoked and deleted"}
