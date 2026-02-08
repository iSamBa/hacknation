"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel


class GoogleAuthorizeResponse(BaseModel):
    """Response from /authorize endpoint."""

    authorization_url: str
    state: str


class GoogleAuthStatusResponse(BaseModel):
    """Response from /status endpoint."""

    connected: bool
    scopes: list[str]
