import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.booking import BookingProvider
from app.models.call_result import CallOutcome, CallResult
from app.models.provider import Provider
from app.services.ranking import (
    earliest_score,
    notes_score,
    rank_results,
    slot_match_score,
)

# ============================================================
# earliest_score Tests
# ============================================================


class TestEarliestScore:
    def test_slot_today_scores_high(self):
        slot = datetime.now(timezone.utc) + timedelta(hours=1)
        score = earliest_score(slot)
        assert score > 0.9

    def test_slot_in_past_returns_one(self):
        slot = datetime.now(timezone.utc) - timedelta(days=1)
        assert earliest_score(slot) == 1.0

    def test_slot_at_max_days_scores_zero(self):
        slot = datetime.now(timezone.utc) + timedelta(days=14)
        assert earliest_score(slot) == pytest.approx(0.0, abs=0.1)

    def test_slot_beyond_max_days_clamps_to_zero(self):
        slot = datetime.now(timezone.utc) + timedelta(days=30)
        assert earliest_score(slot) == 0.0

    def test_slot_at_half_max_scores_half(self):
        slot = datetime.now(timezone.utc) + timedelta(days=7)
        assert earliest_score(slot) == pytest.approx(0.5, abs=0.1)

    def test_custom_max_days(self):
        slot = datetime.now(timezone.utc) + timedelta(days=3)
        assert earliest_score(slot, max_days=3) == pytest.approx(0.0, abs=0.1)

    def test_sooner_scores_higher_than_later(self):
        soon = datetime.now(timezone.utc) + timedelta(days=1)
        later = datetime.now(timezone.utc) + timedelta(days=10)
        assert earliest_score(soon) > earliest_score(later)


# ============================================================
# slot_match_score Tests
# ============================================================


class TestSlotMatchScore:
    def test_no_preferences_returns_neutral(self):
        slot = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        assert slot_match_score(slot, None, None) == 0.5

    def test_exact_date_match(self):
        slot = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, "2026-03-15", None)
        assert score == 0.5  # date match only

    def test_exact_date_and_time_match(self):
        slot = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, "2026-03-15", "morning")
        assert score == 1.0

    def test_date_match_wrong_time(self):
        slot = datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, "2026-03-15", "morning")
        assert score == 0.5  # date match but wrong time

    def test_time_match_wrong_date(self):
        slot = datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, "2026-03-15", "morning")
        assert score == 0.5  # time match but wrong date

    def test_no_match(self):
        slot = datetime(2026, 3, 16, 14, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, "2026-03-15", "morning")
        assert score == 0.25

    def test_afternoon_preference(self):
        slot = datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, None, "afternoon")
        assert score == 0.5

    def test_evening_preference(self):
        slot = datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, None, "evening")
        assert score == 0.5

    def test_specific_time_match(self):
        slot = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, None, "10:00")
        assert score == 0.5

    def test_specific_time_close_match(self):
        slot = datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, None, "10:00")
        assert score == 0.5  # within 1 hour

    def test_relative_date_treated_as_no_date_match(self):
        slot = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        score = slot_match_score(slot, "tomorrow", "morning")
        # "tomorrow" can't be parsed as a date, so no date match
        assert score == 0.5  # time match only


# ============================================================
# notes_score Tests
# ============================================================


class TestNotesScore:
    def test_no_notes_returns_one(self):
        assert notes_score(None) == 1.0

    def test_empty_string_returns_one(self):
        assert notes_score("") == 1.0

    def test_restriction_keyword_lowers_score(self):
        assert notes_score("Requires referral") == 0.3

    def test_cash_only_lowers_score(self):
        assert notes_score("Cash only accepted") == 0.3

    def test_generic_notes_return_medium_score(self):
        assert notes_score("New patients welcome") == 0.7

    def test_case_insensitive(self):
        assert notes_score("REQUIRES REFERRAL") == 0.3


# ============================================================
# rank_results Tests (async, needs mocking)
# ============================================================


def _make_provider_model(**overrides) -> MagicMock:
    provider = MagicMock(spec=Provider)
    provider.id = overrides.get("id", uuid.uuid4())
    provider.place_id = overrides.get("place_id", "place_1")
    provider.name = overrides.get("name", "Test Provider")
    provider.rating = overrides.get("rating", 4.5)
    provider.review_count = overrides.get("review_count", 100)
    return provider


def _make_call_result(
    provider: MagicMock,
    booking_id: uuid.UUID,
    **overrides,
) -> MagicMock:
    cr = MagicMock(spec=CallResult)
    cr.booking_id = booking_id
    cr.provider_id = provider.id
    cr.provider = provider
    cr.call_outcome = overrides.get("call_outcome", CallOutcome.SLOT_OFFERED)
    cr.available_slot = overrides.get(
        "available_slot",
        datetime.now(timezone.utc) + timedelta(days=2),
    )
    cr.provider_notes = overrides.get("provider_notes", None)
    return cr


def _make_booking_provider_model(
    booking_id: uuid.UUID,
    provider_id: uuid.UUID,
    **overrides,
) -> MagicMock:
    bp = MagicMock(spec=BookingProvider)
    bp.booking_id = booking_id
    bp.provider_id = provider_id
    bp.pre_score = overrides.get("pre_score", 0.7)
    bp.travel_minutes = overrides.get("travel_minutes", 15.0)
    bp.was_called = True
    bp.rank = None
    return bp


def _mock_db_execute(booking, call_results, booking_providers):
    """Create a mock db that returns appropriate results per query."""
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # First query: Booking
            result.scalar_one_or_none.return_value = booking
        elif call_count == 2:
            # Second query: CallResults
            result.scalars.return_value.all.return_value = call_results
        elif call_count == 3:
            # Third query: BookingProviders
            result.scalars.return_value.all.return_value = booking_providers
        return result

    return mock_execute


class TestRankResults:
    @pytest.mark.asyncio
    async def test_returns_ranked_results_sorted_by_score(self):
        booking_id = uuid.uuid4()
        booking = MagicMock()
        booking.id = booking_id
        booking.preferred_date = None
        booking.preferred_time = None

        p1 = _make_provider_model(place_id="p1", name="Provider 1")
        p2 = _make_provider_model(place_id="p2", name="Provider 2")

        # p1 has a sooner slot
        cr1 = _make_call_result(
            p1, booking_id,
            available_slot=datetime.now(timezone.utc) + timedelta(days=1),
        )
        # p2 has a later slot
        cr2 = _make_call_result(
            p2, booking_id,
            available_slot=datetime.now(timezone.utc) + timedelta(days=10),
        )

        bp1 = _make_booking_provider_model(booking_id, p1.id, pre_score=0.8)
        bp2 = _make_booking_provider_model(booking_id, p2.id, pre_score=0.8)

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=_mock_db_execute(booking, [cr1, cr2], [bp1, bp2])
        )

        results = await rank_results(db, booking_id)

        assert len(results) == 2
        assert results[0].provider_name == "Provider 1"
        assert results[0].rank == 1
        assert results[1].rank == 2
        assert results[0].score >= results[1].score

    @pytest.mark.asyncio
    async def test_no_positive_outcomes_returns_empty(self):
        booking_id = uuid.uuid4()
        booking = MagicMock()
        booking.id = booking_id
        booking.preferred_date = None
        booking.preferred_time = None

        db = AsyncMock()
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = booking
            elif call_count == 2:
                result.scalars.return_value.all.return_value = []
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        results = await rank_results(db, booking_id)

        assert results == []

    @pytest.mark.asyncio
    async def test_booking_not_found_raises_value_error(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ValueError, match="not found"):
            await rank_results(db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_top_n_limits_results(self):
        booking_id = uuid.uuid4()
        booking = MagicMock()
        booking.id = booking_id
        booking.preferred_date = None
        booking.preferred_time = None

        providers = [
            _make_provider_model(place_id=f"p{i}", name=f"Provider {i}")
            for i in range(10)
        ]
        call_results_list = [
            _make_call_result(
                p, booking_id,
                available_slot=datetime.now(timezone.utc) + timedelta(days=i + 1),
            )
            for i, p in enumerate(providers)
        ]
        bp_list = [
            _make_booking_provider_model(booking_id, p.id, pre_score=0.7)
            for p in providers
        ]

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=_mock_db_execute(booking, call_results_list, bp_list)
        )

        results = await rank_results(db, booking_id, top_n=3)

        assert len(results) == 3
        assert results[0].rank == 1
        assert results[2].rank == 3

    @pytest.mark.asyncio
    async def test_notes_affect_ranking(self):
        booking_id = uuid.uuid4()
        booking = MagicMock()
        booking.id = booking_id
        booking.preferred_date = None
        booking.preferred_time = None

        p1 = _make_provider_model(place_id="p1", name="Restrictive")
        p2 = _make_provider_model(place_id="p2", name="Open")

        same_slot = datetime.now(timezone.utc) + timedelta(days=3)
        cr1 = _make_call_result(
            p1, booking_id,
            available_slot=same_slot,
            provider_notes="Requires referral",
        )
        cr2 = _make_call_result(
            p2, booking_id,
            available_slot=same_slot,
            provider_notes=None,
        )

        bp1 = _make_booking_provider_model(booking_id, p1.id, pre_score=0.7)
        bp2 = _make_booking_provider_model(booking_id, p2.id, pre_score=0.7)

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=_mock_db_execute(booking, [cr1, cr2], [bp1, bp2])
        )

        results = await rank_results(db, booking_id)

        assert results[0].provider_name == "Open"

    @pytest.mark.asyncio
    async def test_result_contains_all_fields(self):
        booking_id = uuid.uuid4()
        booking = MagicMock()
        booking.id = booking_id
        booking.preferred_date = "2026-03-15"
        booking.preferred_time = "morning"

        p1 = _make_provider_model(
            place_id="p1", name="Test Provider", rating=4.5, review_count=50,
        )
        slot = datetime.now(timezone.utc) + timedelta(days=2)
        cr1 = _make_call_result(
            p1, booking_id,
            available_slot=slot,
            provider_notes="New patients welcome",
        )
        bp1 = _make_booking_provider_model(
            booking_id, p1.id, pre_score=0.8, travel_minutes=20.0,
        )

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=_mock_db_execute(booking, [cr1], [bp1])
        )

        results = await rank_results(db, booking_id)

        assert len(results) == 1
        r = results[0]
        assert r.rank == 1
        assert r.provider_id == p1.id
        assert r.provider_name == "Test Provider"
        assert r.place_id == "p1"
        assert r.slot == slot
        assert r.travel_minutes == 20.0
        assert not hasattr(r, "distance_km")
        assert r.rating == 4.5
        assert r.review_count == 50
        assert r.notes == "New patients welcome"
        assert r.call_outcome == "slot_offered"
        assert 0 < r.score <= 1.0

    @pytest.mark.asyncio
    async def test_updates_booking_provider_rank(self):
        booking_id = uuid.uuid4()
        booking = MagicMock()
        booking.id = booking_id
        booking.preferred_date = None
        booking.preferred_time = None

        p1 = _make_provider_model(place_id="p1")
        cr1 = _make_call_result(p1, booking_id)
        bp1 = _make_booking_provider_model(booking_id, p1.id)

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=_mock_db_execute(booking, [cr1], [bp1])
        )

        await rank_results(db, booking_id)

        assert bp1.rank == 1
        db.commit.assert_awaited()
