import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.booking import BookingProvider
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
        for bp in result:
            assert bp.was_called is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_providers(self):
        mock_db = AsyncMock()

        result = await generate_mock_call_results(mock_db, uuid.uuid4(), [])

        assert result == []
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_same_providers_list(self):
        booking_id = uuid.uuid4()
        providers = [_make_booking_provider(booking_id=booking_id)]
        mock_db = AsyncMock()

        result = await generate_mock_call_results(mock_db, booking_id, providers)

        assert result is providers
