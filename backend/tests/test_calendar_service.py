"""Tests for Google Calendar availability service."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_token
from app.models.oauth_token import OAuthToken
from app.services.calendar_service import check_availability, get_calendar_credentials


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_oauth_token():
    """Mock OAuth token with encrypted credentials."""
    token = OAuthToken(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="google",
        access_token=encrypt_token("mock_access_token"),
        refresh_token=encrypt_token("mock_refresh_token"),
        token_expiry=datetime.now(tz=timezone.utc) + timedelta(hours=1),
        scopes=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
    )
    return token


@pytest.mark.asyncio
async def test_check_availability_no_calendar_connected(mock_db):
    """Test availability check when user hasn't connected calendar."""
    # Setup: No token found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    user_id = str(uuid.uuid4())
    start = datetime.now(tz=timezone.utc)
    end = start + timedelta(hours=1)

    # Execute
    result = await check_availability(mock_db, user_id, start, end)

    # Assert
    assert result["available"] is True
    assert result["calendar_connected"] is False
    assert result["conflicts"] == []
    assert "not connected" in result["message"]


@pytest.mark.asyncio
@patch("app.services.calendar_service.build")
async def test_check_availability_no_conflicts(
    mock_build, mock_db, mock_oauth_token
):
    """Test availability check with no conflicts."""
    # Setup: Token found and API returns no busy periods
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_oauth_token
    mock_db.execute.return_value = mock_result

    mock_service = MagicMock()
    mock_freebusy = MagicMock()
    mock_freebusy.query.return_value.execute.return_value = {
        "calendars": {"primary": {"busy": []}}
    }
    mock_service.freebusy.return_value = mock_freebusy
    mock_build.return_value = mock_service

    user_id = str(mock_oauth_token.user_id)
    start = datetime.now(tz=timezone.utc)
    end = start + timedelta(hours=1)

    # Execute
    result = await check_availability(mock_db, user_id, start, end)

    # Assert
    assert result["available"] is True
    assert result["calendar_connected"] is True
    assert result["conflicts"] == []
    assert "message" not in result


@pytest.mark.asyncio
@patch("app.services.calendar_service.build")
async def test_check_availability_with_conflicts(
    mock_build, mock_db, mock_oauth_token
):
    """Test availability check with conflicts."""
    # Setup: Token found and API returns busy periods
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_oauth_token
    mock_db.execute.return_value = mock_result

    conflict_start = "2026-02-08T10:00:00Z"
    conflict_end = "2026-02-08T11:00:00Z"

    mock_service = MagicMock()
    mock_freebusy = MagicMock()
    mock_freebusy.query.return_value.execute.return_value = {
        "calendars": {
            "primary": {"busy": [{"start": conflict_start, "end": conflict_end}]}
        }
    }
    mock_service.freebusy.return_value = mock_freebusy
    mock_build.return_value = mock_service

    user_id = str(mock_oauth_token.user_id)
    start = datetime.now(tz=timezone.utc)
    end = start + timedelta(hours=1)

    # Execute
    result = await check_availability(mock_db, user_id, start, end)

    # Assert
    assert result["available"] is False
    assert result["calendar_connected"] is True
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["start"] == conflict_start
    assert result["conflicts"][0]["end"] == conflict_end


@pytest.mark.asyncio
@patch("app.services.calendar_service.build")
async def test_check_availability_api_error_graceful_degradation(
    mock_build, mock_db, mock_oauth_token
):
    """Test availability check with API error returns available."""
    # Setup: Token found but API raises exception
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_oauth_token
    mock_db.execute.return_value = mock_result

    mock_build.side_effect = Exception("API Error")

    user_id = str(mock_oauth_token.user_id)
    start = datetime.now(tz=timezone.utc)
    end = start + timedelta(hours=1)

    # Execute
    result = await check_availability(mock_db, user_id, start, end)

    # Assert: Graceful degradation
    assert result["available"] is True
    assert result["calendar_connected"] is True
    assert result["conflicts"] == []
    assert "failed" in result["message"]


@pytest.mark.asyncio
@patch("app.services.calendar_service.Request")
async def test_get_calendar_credentials_refreshes_expired_token(
    mock_request, mock_db, mock_oauth_token
):
    """Test that expired tokens are automatically refreshed."""
    # Setup: Token is expired
    mock_oauth_token.token_expiry = datetime.now(tz=timezone.utc) - timedelta(
        hours=1
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_oauth_token
    mock_db.execute.return_value = mock_result

    user_id = str(mock_oauth_token.user_id)

    # Mock credentials refresh
    with patch(
        "app.services.calendar_service.Credentials"
    ) as mock_credentials_class:
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.token = "new_access_token"
        mock_creds.expiry = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        mock_credentials_class.return_value = mock_creds

        # Execute
        credentials = await get_calendar_credentials(mock_db, user_id)

        # Assert: Refresh was called
        assert credentials is not None
        mock_creds.refresh.assert_called_once()
        mock_db.commit.assert_called_once()
