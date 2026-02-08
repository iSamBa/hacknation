import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.booking import Booking, BookingProvider, BookingStatus
from app.models.call_result import CallResult
from app.models.provider import Provider
from app.services.booking_service import confirm_booking


def _make_booking(booking_id: uuid.UUID, status: BookingStatus) -> MagicMock:
    booking = MagicMock(spec=Booking)
    booking.id = booking_id
    booking.status = status
    return booking


def _make_provider(provider_id: uuid.UUID) -> MagicMock:
    provider = MagicMock(spec=Provider)
    provider.id = provider_id
    provider.name = "Test Dentist"
    provider.address = "123 Main St"
    return provider


def _make_booking_provider(
    booking_id: uuid.UUID, provider_id: uuid.UUID
) -> MagicMock:
    bp = MagicMock(spec=BookingProvider)
    bp.booking_id = booking_id
    bp.provider_id = provider_id
    return bp


def _make_call_result(
    booking_id: uuid.UUID, provider_id: uuid.UUID, slot: datetime
) -> MagicMock:
    cr = MagicMock(spec=CallResult)
    cr.booking_id = booking_id
    cr.provider_id = provider_id
    cr.available_slot = slot
    return cr


class TestConfirmBooking:
    @pytest.mark.asyncio
    async def test_confirms_booking_successfully(self):
        booking_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        slot = datetime.now(timezone.utc) + timedelta(days=2)

        booking = _make_booking(booking_id, BookingStatus.OPTIONS_READY)
        bp = _make_booking_provider(booking_id, provider_id)
        cr = _make_call_result(booking_id, provider_id, slot)
        provider = _make_provider(provider_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = booking
            elif call_count == 2:
                result.scalar_one_or_none.return_value = bp
            elif call_count == 3:
                result.scalar_one_or_none.return_value = cr
            elif call_count == 4:
                result.scalar_one_or_none.return_value = provider
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        response = await confirm_booking(db, booking_id, provider_id, slot)

        assert response.id == booking_id
        assert response.status == BookingStatus.CONFIRMED
        assert response.provider_name == "Test Dentist"
        assert response.provider_address == "123 Main St"
        assert response.slot == slot
        assert booking.status == BookingStatus.CONFIRMED
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_when_already_confirmed(self):
        booking_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        slot = datetime.now(timezone.utc) + timedelta(days=2)

        booking = _make_booking(booking_id, BookingStatus.CONFIRMED)
        provider = _make_provider(provider_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = booking
            elif call_count == 2:
                result.scalar_one_or_none.return_value = provider
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        response = await confirm_booking(db, booking_id, provider_id, slot)

        assert response.id == booking_id
        assert response.status == BookingStatus.CONFIRMED
        assert response.provider_name == "Test Dentist"
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_for_booking_not_found(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ValueError, match="not found"):
            await confirm_booking(
                db,
                uuid.uuid4(),
                uuid.uuid4(),
                datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_raises_for_wrong_status(self):
        booking_id = uuid.uuid4()
        booking = _make_booking(booking_id, BookingStatus.SEARCHING)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = booking
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ValueError, match="options_ready"):
            await confirm_booking(
                db,
                booking_id,
                uuid.uuid4(),
                datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_raises_for_provider_not_in_shortlist(self):
        booking_id = uuid.uuid4()
        booking = _make_booking(booking_id, BookingStatus.OPTIONS_READY)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = booking
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="not in the shortlist"):
            await confirm_booking(
                db,
                booking_id,
                uuid.uuid4(),
                datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_raises_for_invalid_slot(self):
        booking_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        wrong_slot = datetime.now(timezone.utc) + timedelta(days=5)

        booking = _make_booking(booking_id, BookingStatus.OPTIONS_READY)
        bp = _make_booking_provider(booking_id, provider_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = booking
            elif call_count == 2:
                result.scalar_one_or_none.return_value = bp
            elif call_count == 3:
                result.scalar_one_or_none.return_value = None
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="not offered"):
            await confirm_booking(db, booking_id, provider_id, wrong_slot)


class TestCalendarEventCreation:
    @pytest.mark.asyncio
    async def test_skips_when_calendar_not_connected(self):
        """Test that calendar event creation returns None when not connected."""
        from app.services.calendar_service import create_calendar_event

        # Mock DB that returns no OAuth token
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        slot = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        event = await create_calendar_event(
            db=db,
            user_id=str(uuid.uuid4()),
            provider_name="Test Dentist",
            provider_address="123 Main St",
            slot=slot,
            service_type="dentist",
            booking_id=str(uuid.uuid4()),
        )

        # Should return None when calendar not connected
        assert event is None
