import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.booking import Booking, BookingProvider, BookingStatus
from app.schemas.intent import BookingIntent
from app.services.booking_service import (
    create_booking,
    get_booking,
    get_shortlist,
    list_bookings,
    save_shortlist,
)
from app.services.provider_search import ProviderResult
from app.services.scoring import ScoredProvider


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


def _make_scored_provider(
    place_id: str = "place_1",
    score: float = 0.85,
    travel_minutes: float = 10.0,
    **provider_overrides,
) -> ScoredProvider:
    """Create a ScoredProvider for testing."""
    provider_defaults = {
        "place_id": place_id,
        "name": "Test Provider",
        "address": "123 Main St",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "rating": 4.5,
        "review_count": 100,
        "is_open": True,
        "phone": "(555) 123-4567",
    }
    provider_defaults.update(provider_overrides)
    return ScoredProvider(
        provider=ProviderResult(**provider_defaults),
        score=score,
        travel_minutes=travel_minutes,
    )


def _make_db_provider(place_id: str = "place_1", **overrides) -> MagicMock:
    """Create a mock Provider DB model."""
    provider_id = overrides.pop("id", uuid.uuid4())
    defaults = {
        "id": provider_id,
        "place_id": place_id,
        "name": "Test Provider",
        "address": "123 Main St",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "phone": "(555) 123-4567",
        "rating": 4.5,
        "review_count": 100,
        "is_open": True,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestSaveShortlist:
    @pytest.mark.asyncio
    async def test_saves_scored_providers_as_booking_providers(self):
        booking_id = uuid.uuid4()
        db_provider = _make_db_provider(place_id="p1")
        mock_booking = _make_booking(id=booking_id)

        # First execute: Provider lookup
        mock_provider_scalars = MagicMock()
        mock_provider_scalars.all.return_value = [db_provider]
        mock_provider_result = MagicMock()
        mock_provider_result.scalars.return_value = mock_provider_scalars

        # Second execute: Booking lookup
        mock_booking_result = MagicMock()
        mock_booking_result.scalar_one_or_none.return_value = mock_booking

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            mock_provider_result,
            mock_booking_result,
        ]
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        scored = [_make_scored_provider(place_id="p1", score=0.9)]
        result = await save_shortlist(mock_db, booking_id, scored)

        assert len(result) == 1
        assert result[0].booking_id == booking_id
        assert result[0].provider_id == db_provider.id
        assert result[0].pre_score == 0.9
        assert result[0].rank == 1
        assert len(added_objects) == 1
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_booking_status_to_shortlisting(self):
        booking_id = uuid.uuid4()
        db_provider = _make_db_provider(place_id="p1")
        mock_booking = _make_booking(id=booking_id)

        mock_provider_scalars = MagicMock()
        mock_provider_scalars.all.return_value = [db_provider]
        mock_provider_result = MagicMock()
        mock_provider_result.scalars.return_value = mock_provider_scalars

        mock_booking_result = MagicMock()
        mock_booking_result.scalar_one_or_none.return_value = mock_booking

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            mock_provider_result,
            mock_booking_result,
        ]
        mock_db.add = MagicMock()

        scored = [_make_scored_provider(place_id="p1")]
        await save_shortlist(mock_db, booking_id, scored)

        assert mock_booking.status == BookingStatus.SHORTLISTING

    @pytest.mark.asyncio
    async def test_assigns_ranks_in_order(self):
        booking_id = uuid.uuid4()
        db_p1 = _make_db_provider(place_id="p1")
        db_p2 = _make_db_provider(place_id="p2")
        mock_booking = _make_booking(id=booking_id)

        mock_provider_scalars = MagicMock()
        mock_provider_scalars.all.return_value = [db_p1, db_p2]
        mock_provider_result = MagicMock()
        mock_provider_result.scalars.return_value = mock_provider_scalars

        mock_booking_result = MagicMock()
        mock_booking_result.scalar_one_or_none.return_value = mock_booking

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            mock_provider_result,
            mock_booking_result,
        ]
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        scored = [
            _make_scored_provider(place_id="p1", score=0.9),
            _make_scored_provider(place_id="p2", score=0.7),
        ]
        result = await save_shortlist(mock_db, booking_id, scored)

        assert len(result) == 2
        assert result[0].rank == 1
        assert result[1].rank == 2

    @pytest.mark.asyncio
    async def test_skips_providers_not_in_db(self):
        booking_id = uuid.uuid4()
        mock_booking = _make_booking(id=booking_id)

        mock_provider_scalars = MagicMock()
        mock_provider_scalars.all.return_value = []  # No providers in DB
        mock_provider_result = MagicMock()
        mock_provider_result.scalars.return_value = mock_provider_scalars

        mock_booking_result = MagicMock()
        mock_booking_result.scalar_one_or_none.return_value = mock_booking

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            mock_provider_result,
            mock_booking_result,
        ]
        mock_db.add = MagicMock()

        scored = [_make_scored_provider(place_id="unknown")]
        result = await save_shortlist(mock_db, booking_id, scored)

        assert len(result) == 0
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_scored_providers_returns_empty(self):
        mock_db = AsyncMock()
        result = await save_shortlist(mock_db, uuid.uuid4(), [])
        assert result == []
        mock_db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handles_integrity_error(self):
        from sqlalchemy.exc import IntegrityError

        booking_id = uuid.uuid4()
        db_provider = _make_db_provider(place_id="p1")
        mock_booking = _make_booking(id=booking_id)

        mock_provider_scalars = MagicMock()
        mock_provider_scalars.all.return_value = [db_provider]
        mock_provider_result = MagicMock()
        mock_provider_result.scalars.return_value = mock_provider_scalars

        mock_booking_result = MagicMock()
        mock_booking_result.scalar_one_or_none.return_value = mock_booking

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [
            mock_provider_result,
            mock_booking_result,
        ]
        mock_db.add = MagicMock()
        mock_db.commit.side_effect = IntegrityError(
            "duplicate", {}, Exception()
        )

        scored = [_make_scored_provider(place_id="p1")]
        result = await save_shortlist(mock_db, booking_id, scored)

        assert result == []
        mock_db.rollback.assert_awaited_once()


class TestGetShortlist:
    @pytest.mark.asyncio
    async def test_returns_shortlist_items(self):
        provider_id = uuid.uuid4()
        db_provider = _make_db_provider(
            place_id="p1", id=provider_id, name="Good Dentist"
        )

        bp = MagicMock(spec=BookingProvider)
        bp.rank = 1
        bp.pre_score = 0.85
        bp.travel_minutes = 12.5
        bp.provider_id = provider_id
        bp.provider = db_provider

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [bp]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_shortlist(mock_db, uuid.uuid4())

        assert len(result) == 1
        assert result[0].rank == 1
        assert result[0].provider_name == "Good Dentist"
        assert result[0].pre_score == 0.85
        assert result[0].travel_minutes == 12.5
        assert result[0].place_id == "p1"
        assert result[0].rating == 4.5
        assert result[0].provider_id == provider_id

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_shortlist(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_shortlist(mock_db, uuid.uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_items_ordered(self):
        bp1 = MagicMock(spec=BookingProvider)
        bp1.rank = 1
        bp1.pre_score = 0.90
        bp1.travel_minutes = 5.0
        bp1.provider_id = uuid.uuid4()
        bp1.provider = _make_db_provider(place_id="p1", name="Best Dentist")

        bp2 = MagicMock(spec=BookingProvider)
        bp2.rank = 2
        bp2.pre_score = 0.75
        bp2.travel_minutes = 20.0
        bp2.provider_id = uuid.uuid4()
        bp2.provider = _make_db_provider(place_id="p2", name="OK Dentist")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [bp1, bp2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_shortlist(mock_db, uuid.uuid4())

        assert len(result) == 2
        assert result[0].rank == 1
        assert result[0].provider_name == "Best Dentist"
        assert result[1].rank == 2
        assert result[1].provider_name == "OK Dentist"
