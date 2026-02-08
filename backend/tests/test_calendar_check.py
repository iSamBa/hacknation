"""Tests for calendar availability checking service."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile
from app.services.calendar_check import check_user_availability


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock user profile."""
    return UserProfile(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        address="123 Test St",
        latitude=40.7128,
        longitude=-74.0060,
    )


@pytest.mark.asyncio
@patch("app.services.calendar_check.check_availability")
@patch("app.services.calendar_check.get_or_create_default_user")
async def test_check_user_availability_success(
    mock_get_user, mock_check_avail, mock_db, mock_user
):
    """Test successful availability check."""
    # Setup
    mock_get_user.return_value = mock_user
    mock_check_avail.return_value = {
        "available": True,
        "calendar_connected": True,
        "conflicts": [],
    }

    # Execute
    result = await check_user_availability(mock_db, "2026-02-08", "10:00")

    # Assert
    assert result["available"] is True
    assert result["calendar_connected"] is True
    assert result["conflicts"] == []

    # Verify datetime range (1 hour slot)
    call_args = mock_check_avail.call_args
    start, end = call_args[0][2], call_args[0][3]
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert (end - start) == timedelta(hours=1)


@pytest.mark.asyncio
@patch("app.services.calendar_check.check_availability")
@patch("app.services.calendar_check.get_or_create_default_user")
async def test_check_user_availability_with_conflicts(
    mock_get_user, mock_check_avail, mock_db, mock_user
):
    """Test availability check with conflicts."""
    # Setup
    mock_get_user.return_value = mock_user
    mock_check_avail.return_value = {
        "available": False,
        "calendar_connected": True,
        "conflicts": [
            {
                "start": "2026-02-08T10:00:00Z",
                "end": "2026-02-08T11:00:00Z",
            }
        ],
    }

    # Execute
    result = await check_user_availability(mock_db, "2026-02-08", "10:00")

    # Assert
    assert result["available"] is False
    assert len(result["conflicts"]) == 1


@pytest.mark.asyncio
@patch("app.services.calendar_check.check_availability")
@patch("app.services.calendar_check.get_or_create_default_user")
async def test_check_user_availability_calendar_not_connected(
    mock_get_user, mock_check_avail, mock_db, mock_user
):
    """Test availability check when calendar not connected."""
    # Setup
    mock_get_user.return_value = mock_user
    mock_check_avail.return_value = {
        "available": True,
        "calendar_connected": False,
        "conflicts": [],
        "message": "Calendar not connected — assuming available",
    }

    # Execute
    result = await check_user_availability(mock_db, "2026-02-08", "10:00")

    # Assert
    assert result["available"] is True
    assert result["calendar_connected"] is False
    assert "not connected" in result["message"]


@pytest.mark.asyncio
@patch("app.services.calendar_check.check_availability")
@patch("app.services.calendar_check.get_or_create_default_user")
async def test_check_user_availability_parses_datetime_correctly(
    mock_get_user, mock_check_avail, mock_db, mock_user
):
    """Test that date and time are parsed into correct datetime range."""
    # Setup
    mock_get_user.return_value = mock_user
    mock_check_avail.return_value = {
        "available": True,
        "calendar_connected": True,
        "conflicts": [],
    }

    # Execute with specific date and time
    await check_user_availability(mock_db, "2026-02-15", "14:30")

    # Assert: Verify the datetime parameters
    call_args = mock_check_avail.call_args[0]
    start = call_args[2]
    end = call_args[3]

    assert start.year == 2026
    assert start.month == 2
    assert start.day == 15
    assert start.hour == 14
    assert start.minute == 30

    assert end.year == 2026
    assert end.month == 2
    assert end.day == 15
    assert end.hour == 15
    assert end.minute == 30
