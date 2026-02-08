import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.booking import Booking, BookingStatus
from app.schemas.intent import BookingIntent
from app.services.booking_service import (
    create_booking,
    get_booking,
    list_bookings,
)


def _make_booking(**overrides) -> MagicMock:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "status": BookingStatus.SEARCHING,
        "service_type": "dentist",
        "preferred_date": None,
        "preferred_time": None,
        "location_override": None,
        "constraints": None,
        "raw_message": "I need a dentist",
    }
    defaults.update(overrides)
    booking = MagicMock(spec=Booking)
    for k, v in defaults.items():
        setattr(booking, k, v)
    return booking


class TestCreateBooking:
    @pytest.mark.asyncio
    async def test_creates_booking_with_parsed_intent(self):
        intent = BookingIntent(
            service_type="dentist",
            date="2026-02-10",
            time_preference="afternoon",
            urgency="specific_date",
        )
        user_id = uuid.uuid4()
        mock_db = AsyncMock()

        with patch(
            "app.services.booking_service.parse_booking_intent",
            return_value=intent,
        ) as mock_parse:
            # Make db.refresh set attributes on the booking
            mock_db.refresh = AsyncMock()

            # Capture the Booking object added to db
            added_objects = []

            def capture_add(obj):
                added_objects.append(obj)

            mock_db.add = capture_add

            _booking, returned_intent = await create_booking(
                mock_db, user_id, "I need a dentist next Tuesday afternoon"
            )

        mock_parse.assert_awaited_once_with(
            "I need a dentist next Tuesday afternoon"
        )
        assert returned_intent.service_type == "dentist"
        assert len(added_objects) == 1
        added_booking = added_objects[0]
        assert added_booking.service_type == "dentist"
        assert added_booking.preferred_date == "2026-02-10"
        assert added_booking.preferred_time == "afternoon"
        assert added_booking.status == BookingStatus.SEARCHING
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_booking_with_pre_parsed_intent(self):
        intent = BookingIntent(
            service_type="plumber",
            urgency="asap",
        )
        user_id = uuid.uuid4()
        mock_db = AsyncMock()
        mock_db.refresh = AsyncMock()
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        _booking, returned_intent = await create_booking(
            mock_db, user_id, "Plumber ASAP", intent=intent
        )

        assert returned_intent.service_type == "plumber"
        assert len(added_objects) == 1
        assert added_objects[0].service_type == "plumber"
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_on_parse_error(self):
        mock_db = AsyncMock()
        user_id = uuid.uuid4()

        with patch(
            "app.services.booking_service.parse_booking_intent",
            side_effect=ValueError("Message cannot be empty"),
        ):
            with pytest.raises(ValueError, match="Message cannot be empty"):
                await create_booking(mock_db, user_id, "")


class TestGetBooking:
    @pytest.mark.asyncio
    async def test_returns_booking_when_found(self):
        booking_id = uuid.uuid4()
        mock_booking = _make_booking(id=booking_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_booking
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_booking(mock_db, booking_id)

        assert result is mock_booking
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_booking(mock_db, uuid.uuid4())

        assert result is None


class TestListBookings:
    @pytest.mark.asyncio
    async def test_returns_user_bookings(self):
        user_id = uuid.uuid4()
        bookings = [_make_booking(user_id=user_id) for _ in range(3)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = bookings
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await list_bookings(mock_db, user_id)

        assert len(result) == 3
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await list_bookings(mock_db, uuid.uuid4())

        assert result == []
