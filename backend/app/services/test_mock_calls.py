import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.booking import BookingProvider
from app.models.call_result import CallOutcome
from app.services.mock_calls import generate_mock_call_results


def _make_booking_provider(**overrides) -> MagicMock:
    bp = MagicMock(spec=BookingProvider)
    bp.booking_id = overrides.get("booking_id", uuid.uuid4())
    bp.provider_id = overrides.get("provider_id", uuid.uuid4())
    bp.was_called = False
    return bp


class TestGenerateMockCallResults:
    @pytest.mark.asyncio
    async def test_marks_all_providers_as_called(self):
        booking_id = uuid.uuid4()
        providers = [_make_booking_provider(booking_id=booking_id) for _ in range(3)]
        mock_db = AsyncMock()

        result = await generate_mock_call_results(mock_db, booking_id, providers)

        assert len(result) == 3
        for bp in providers:
            assert bp.was_called is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_providers(self):
        mock_db = AsyncMock()

        result = await generate_mock_call_results(mock_db, uuid.uuid4(), [])

        assert result == []
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_creates_call_result_records(self):
        booking_id = uuid.uuid4()
        providers = [_make_booking_provider(booking_id=booking_id)]
        mock_db = AsyncMock()

        result = await generate_mock_call_results(mock_db, booking_id, providers)

        assert len(result) == 1
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_results_have_valid_outcomes(self):
        booking_id = uuid.uuid4()
        providers = [_make_booking_provider(booking_id=booking_id) for _ in range(20)]
        mock_db = AsyncMock()

        results = await generate_mock_call_results(mock_db, booking_id, providers)

        valid_outcomes = {o.value for o in CallOutcome}
        for cr in results:
            assert cr.call_outcome.value in valid_outcomes

    @pytest.mark.asyncio
    async def test_positive_outcomes_have_slots(self):
        booking_id = uuid.uuid4()
        providers = [_make_booking_provider(booking_id=booking_id) for _ in range(50)]
        mock_db = AsyncMock()

        results = await generate_mock_call_results(mock_db, booking_id, providers)

        for cr in results:
            positive = (CallOutcome.SLOT_OFFERED, CallOutcome.BOOKED_TENTATIVE)
            if cr.call_outcome in positive:
                assert cr.available_slot is not None
            else:
                assert cr.available_slot is None
