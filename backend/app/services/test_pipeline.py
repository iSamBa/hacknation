import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.booking import Booking, BookingProvider, BookingStatus
from app.models.user import UserProfile
from app.services.distance_service import DistanceResult
from app.services.pipeline import run_booking_pipeline
from app.services.provider_search import ProviderResult
from app.services.scoring import ScoredProvider


def _make_booking(**overrides) -> MagicMock:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "status": BookingStatus.SEARCHING,
        "service_type": "dentist",
    }
    defaults.update(overrides)
    booking = MagicMock(spec=Booking)
    for k, v in defaults.items():
        setattr(booking, k, v)
    return booking


def _make_user(**overrides) -> MagicMock:
    defaults = {
        "id": uuid.uuid4(),
        "latitude": 40.7128,
        "longitude": -74.0060,
        "max_distance_km": 10.0,
        "min_rating": 4.0,
        "blocked_providers": [],
        "preferred_providers": [],
    }
    defaults.update(overrides)
    user = MagicMock(spec=UserProfile)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_provider_result(**overrides) -> ProviderResult:
    defaults = {
        "place_id": "place_1",
        "name": "Test Dentist",
        "address": "123 Main St",
        "latitude": 40.7200,
        "longitude": -74.0100,
        "rating": 4.5,
        "review_count": 100,
        "is_open": True,
        "phone": "(555) 123-4567",
    }
    defaults.update(overrides)
    return ProviderResult(**defaults)


def _make_scored_provider(**overrides) -> ScoredProvider:
    provider = _make_provider_result(**overrides.pop("provider_overrides", {}))
    defaults = {
        "provider": provider,
        "score": 0.85,
        "travel_minutes": 10.0,
    }
    defaults.update(overrides)
    return ScoredProvider(**defaults)


def _mock_db_execute_chain(booking, user, booking_providers=None):
    """Create a mock db whose execute() returns booking, then user, etc.

    The pipeline calls db.execute() multiple times for:
    1. Load booking
    2. _update_status (SEARCHING) - load booking
    3. _update_status (SEARCHING) - commit handled separately
    ... and so on.

    We use side_effect to return the right scalar for each call.
    """
    mock_db = AsyncMock()

    # We'll use a simpler approach: make execute always return a result
    # whose scalar_one_or_none returns the right thing based on call order.
    call_count = 0

    def make_result(value):
        r = MagicMock()
        r.scalar_one_or_none.return_value = value
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = booking_providers or []
        r.scalars.return_value = scalars_mock
        return r

    async def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # All booking lookups return the booking, user lookups return user
        # This works because _update_status and _get_user both do
        # scalar_one_or_none, and the booking mock has the right attributes
        return make_result(booking)

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    return mock_db


class TestRunBookingPipeline:
    @pytest.mark.asyncio
    async def test_happy_path_completes_pipeline(self):
        booking_id = uuid.uuid4()
        user_id = uuid.uuid4()
        booking = _make_booking(id=booking_id, user_id=user_id)
        user = _make_user(id=user_id)

        providers = [_make_provider_result()]
        distances = [
            DistanceResult(distance_km=5.0, duration_minutes=10.0, status="ok")
        ]
        scored = [_make_scored_provider()]
        bp_records = [MagicMock(spec=BookingProvider, was_called=False)]

        mock_db = AsyncMock()

        # Track status changes
        status_changes = []
        original_status = booking.status

        def track_status(val):
            status_changes.append(val)

        type(booking).status = property(
            lambda self: status_changes[-1] if status_changes else original_status,
            lambda self, val: track_status(val),
        )

        # Make db.execute return appropriate results
        booking_result = MagicMock()
        booking_result.scalar_one_or_none.return_value = booking
        bp_scalars = MagicMock()
        bp_scalars.all.return_value = bp_records
        bp_result = MagicMock()
        bp_result.scalars.return_value = bp_scalars

        # All execute calls: first returns booking, _update_status calls return
        # booking, _get_user returns user, _get_booking_providers returns bp_result
        call_idx = [0]

        async def mock_execute(*args, **kwargs):
            call_idx[0] += 1
            return booking_result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        with (
            patch(
                "app.services.pipeline._get_user",
                return_value=user,
            ) as mock_get_user,
            patch(
                "app.services.pipeline.search_providers",
                return_value=providers,
            ) as mock_search,
            patch(
                "app.services.pipeline.calculate_distances",
                return_value=distances,
            ) as mock_distances,
            patch(
                "app.services.pipeline.score_providers",
                return_value=scored,
            ) as mock_score,
            patch(
                "app.services.pipeline.save_shortlist",
                return_value=bp_records,
            ) as mock_save,
            patch(
                "app.services.pipeline._get_booking_providers",
                return_value=bp_records,
            ) as mock_get_bps,
            patch(
                "app.services.pipeline.generate_mock_call_results",
                return_value=bp_records,
            ) as mock_calls,
        ):
            await run_booking_pipeline(booking_id, mock_db)

        mock_get_user.assert_awaited_once_with(mock_db, user_id)
        mock_search.assert_awaited_once()
        mock_distances.assert_awaited_once()
        mock_score.assert_called_once()
        mock_save.assert_awaited_once()
        mock_get_bps.assert_awaited_once_with(mock_db, booking_id)
        mock_calls.assert_awaited_once()

        # Verify status transitions happened
        assert BookingStatus.SEARCHING in status_changes
        assert BookingStatus.SHORTLISTING in status_changes
        assert BookingStatus.CALLING in status_changes
        assert BookingStatus.OPTIONS_READY in status_changes

    @pytest.mark.asyncio
    async def test_no_providers_found_sets_call_failed(self):
        booking_id = uuid.uuid4()
        user_id = uuid.uuid4()
        booking = _make_booking(id=booking_id, user_id=user_id)
        user = _make_user(id=user_id)

        status_changes = []

        _default = BookingStatus.SEARCHING
        type(booking).status = property(
            lambda self: status_changes[-1] if status_changes else _default,
            lambda self, val: status_changes.append(val),
        )

        booking_result = MagicMock()
        booking_result.scalar_one_or_none.return_value = booking
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=booking_result)

        with (
            patch("app.services.pipeline._get_user", return_value=user),
            patch("app.services.pipeline.search_providers", return_value=[]),
        ):
            await run_booking_pipeline(booking_id, mock_db)

        assert BookingStatus.CALL_FAILED in status_changes

    @pytest.mark.asyncio
    async def test_error_in_distance_sets_call_failed(self):
        booking_id = uuid.uuid4()
        user_id = uuid.uuid4()
        booking = _make_booking(id=booking_id, user_id=user_id)
        user = _make_user(id=user_id)

        providers = [_make_provider_result()]
        status_changes = []

        _default = BookingStatus.SEARCHING
        type(booking).status = property(
            lambda self: status_changes[-1] if status_changes else _default,
            lambda self, val: status_changes.append(val),
        )

        booking_result = MagicMock()
        booking_result.scalar_one_or_none.return_value = booking
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=booking_result)
        mock_db.in_transaction = MagicMock(return_value=False)

        with (
            patch("app.services.pipeline._get_user", return_value=user),
            patch(
                "app.services.pipeline.search_providers",
                return_value=providers,
            ),
            patch(
                "app.services.pipeline.calculate_distances",
                side_effect=ValueError("API error"),
            ),
        ):
            await run_booking_pipeline(booking_id, mock_db)

        assert BookingStatus.CALL_FAILED in status_changes

    @pytest.mark.asyncio
    async def test_booking_not_found_returns_early(self):
        booking_id = uuid.uuid4()
        booking_result = MagicMock()
        booking_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=booking_result)

        # Should not raise
        await run_booking_pipeline(booking_id, mock_db)

        # Only the initial booking lookup should have happened
        mock_db.execute.assert_awaited_once()


class TestStartPipeline:
    def test_creates_asyncio_task(self):
        import asyncio

        from app.services.pipeline import start_pipeline

        booking_id = uuid.uuid4()

        async def run():
            with patch(
                "app.services.pipeline._run_pipeline_with_session",
                return_value=None,
            ):
                task = start_pipeline(booking_id)
                assert isinstance(task, asyncio.Task)
                assert f"pipeline-{booking_id}" == task.get_name()
                task.cancel()

        asyncio.run(run())
