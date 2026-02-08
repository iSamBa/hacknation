from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import googlemaps.exceptions
import pytest

from app.services.provider_search import (
    ProviderResult,
    _parse_place,
    _provider_to_result,
    _search_places,
    cache_providers,
    enrich_with_phone,
    get_cached_providers,
    search_providers,
)


def _make_place(**overrides) -> dict:
    """Create a fake Google Places result."""
    defaults = {
        "place_id": "ChIJ_test123",
        "name": "Test Dentist",
        "vicinity": "123 Main St",
        "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
        "rating": 4.5,
        "user_ratings_total": 120,
        "opening_hours": {"open_now": True},
    }
    defaults.update(overrides)
    return defaults


def _make_provider_result(**overrides) -> ProviderResult:
    """Create a ProviderResult for testing."""
    defaults = {
        "place_id": "ChIJ_test123",
        "name": "Test Dentist",
        "address": "123 Main St",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "rating": 4.5,
        "review_count": 120,
        "is_open": True,
        "phone": None,
    }
    defaults.update(overrides)
    return ProviderResult(**defaults)


def _make_cached_provider(**overrides) -> MagicMock:
    """Create a mock cached Provider model."""
    defaults = {
        "place_id": "ChIJ_cached",
        "name": "Cached Dentist",
        "address": "456 Oak Ave",
        "latitude": 40.7,
        "longitude": -74.0,
        "rating": 4.0,
        "review_count": 50,
        "is_open": True,
        "phone": "(555) 123-4567",
        "cached_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ============================================================
# ProviderResult Schema Tests
# ============================================================


class TestProviderResult:
    def test_valid_result(self):
        result = ProviderResult(
            place_id="ChIJ_test",
            name="Test Provider",
            address="123 Main St",
            latitude=40.7128,
            longitude=-74.0060,
            rating=4.5,
            review_count=100,
            is_open=True,
        )
        assert result.place_id == "ChIJ_test"
        assert result.name == "Test Provider"
        assert result.latitude == 40.7128

    def test_defaults(self):
        result = ProviderResult(
            place_id="ChIJ_test",
            name="Test Provider",
            latitude=0.0,
            longitude=0.0,
        )
        assert result.address == ""
        assert result.rating == 0.0
        assert result.review_count == 0
        assert result.is_open is None
        assert result.phone is None

    def test_phone_field(self):
        result = ProviderResult(
            place_id="ChIJ_test",
            name="Test Provider",
            latitude=0.0,
            longitude=0.0,
            phone="(555) 123-4567",
        )
        assert result.phone == "(555) 123-4567"


# ============================================================
# _parse_place Tests
# ============================================================


class TestParsePlace:
    def test_parses_complete_place(self):
        place = _make_place()
        result = _parse_place(place)

        assert result is not None
        assert result.place_id == "ChIJ_test123"
        assert result.name == "Test Dentist"
        assert result.address == "123 Main St"
        assert result.latitude == 40.7128
        assert result.longitude == -74.0060
        assert result.rating == 4.5
        assert result.review_count == 120
        assert result.is_open is True

    def test_parses_minimal_place(self):
        place = {
            "place_id": "ChIJ_min",
            "name": "Minimal Place",
            "geometry": {"location": {"lat": 0.0, "lng": 0.0}},
        }
        result = _parse_place(place)

        assert result is not None
        assert result.place_id == "ChIJ_min"
        assert result.name == "Minimal Place"
        assert result.address == ""
        assert result.rating == 0.0
        assert result.review_count == 0
        assert result.is_open is None

    def test_malformed_place_returns_none(self):
        place = {"name": "No place_id"}
        result = _parse_place(place)
        assert result is None

    def test_missing_geometry_returns_none(self):
        place = {"place_id": "ChIJ_test", "name": "No geometry"}
        result = _parse_place(place)
        assert result is None


# ============================================================
# _provider_to_result Tests
# ============================================================


class TestProviderToResult:
    def test_converts_cached_provider(self):
        provider = _make_cached_provider()
        result = _provider_to_result(provider)

        assert result.place_id == "ChIJ_cached"
        assert result.name == "Cached Dentist"
        assert result.phone == "(555) 123-4567"
        assert result.latitude == 40.7
        assert result.longitude == -74.0


# ============================================================
# enrich_with_phone Tests
# ============================================================


class TestEnrichWithPhone:
    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_enriches_providers_with_phone(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.place.return_value = {
            "result": {"formatted_phone_number": "(555) 111-2222"}
        }

        providers = [_make_provider_result(place_id="p1")]
        results = await enrich_with_phone(providers)

        assert len(results) == 1
        assert results[0].phone == "(555) 111-2222"
        assert results[0].place_id == "p1"
        mock_client.place.assert_called_once_with(
            "p1", fields=["formatted_phone_number"]
        )

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_filters_out_providers_without_phone(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.place.side_effect = [
            {"result": {"formatted_phone_number": "(555) 111-2222"}},
            {"result": {}},  # No phone
            {"result": {"formatted_phone_number": "(555) 333-4444"}},
        ]

        providers = [
            _make_provider_result(place_id="p1"),
            _make_provider_result(place_id="p2"),
            _make_provider_result(place_id="p3"),
        ]
        results = await enrich_with_phone(providers)

        assert len(results) == 2
        assert results[0].place_id == "p1"
        assert results[1].place_id == "p3"

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_handles_api_error_during_enrichment(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.place.side_effect = [
            googlemaps.exceptions.ApiError("ERROR"),
            {"result": {"formatted_phone_number": "(555) 222-3333"}},
        ]

        providers = [
            _make_provider_result(place_id="p1"),
            _make_provider_result(place_id="p2"),
        ]
        results = await enrich_with_phone(providers)

        assert len(results) == 1
        assert results[0].place_id == "p2"

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_empty_providers_list(self, mock_get_client):
        results = await enrich_with_phone([])
        assert results == []


# ============================================================
# get_cached_providers Tests
# ============================================================


class TestGetCachedProviders:
    @pytest.mark.asyncio
    async def test_returns_fresh_cached_providers(self):
        fresh_provider = _make_cached_provider(
            cached_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [fresh_provider]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        results = await get_cached_providers(mock_db, ["ChIJ_cached"])

        assert len(results) == 1
        assert results[0].place_id == "ChIJ_cached"
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_place_ids_returns_empty(self):
        mock_db = AsyncMock()
        results = await get_cached_providers(mock_db, [])
        assert results == []
        mock_db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_cached_providers_returns_empty(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        results = await get_cached_providers(mock_db, ["ChIJ_unknown"])

        assert results == []


# ============================================================
# cache_providers Tests
# ============================================================


class TestCacheProviders:
    @pytest.mark.asyncio
    async def test_creates_new_provider_when_not_cached(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        providers = [
            _make_provider_result(
                place_id="new1", phone="(555) 111-2222"
            )
        ]
        await cache_providers(mock_db, providers)

        assert len(added_objects) == 1
        assert added_objects[0].place_id == "new1"
        assert added_objects[0].phone == "(555) 111-2222"
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_existing_provider(self):
        existing = MagicMock()
        existing.place_id = "existing1"
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [existing]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        providers = [
            _make_provider_result(
                place_id="existing1",
                name="Updated Name",
                phone="(555) 999-8888",
            )
        ]
        await cache_providers(mock_db, providers)

        assert existing.name == "Updated Name"
        assert existing.phone == "(555) 999-8888"
        assert existing.cached_at is not None
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_providers_skips_db(self):
        mock_db = AsyncMock()
        await cache_providers(mock_db, [])
        mock_db.execute.assert_not_awaited()
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handles_integrity_error(self):
        from sqlalchemy.exc import IntegrityError

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.commit.side_effect = IntegrityError(
            "duplicate", {}, Exception()
        )

        providers = [
            _make_provider_result(
                place_id="race1", phone="(555) 111-2222"
            )
        ]
        # Should not raise
        await cache_providers(mock_db, providers)

        mock_db.rollback.assert_awaited_once()


# ============================================================
# _search_places Tests (raw API search, no caching)
# ============================================================


class TestSearchPlaces:
    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_returns_providers(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.return_value = {
            "results": [
                _make_place(place_id="place1", name="Dentist A"),
                _make_place(place_id="place2", name="Dentist B"),
            ],
        }

        results = await _search_places("dentist", 40.7128, -74.0060, 10.0)

        assert len(results) == 2
        assert results[0].place_id == "place1"
        assert results[1].place_id == "place2"

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_empty_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.return_value = {"results": []}

        results = await _search_places("obscure_service", 40.7128, -74.0060)

        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_api_error_raises_value_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.side_effect = (
            googlemaps.exceptions.ApiError("REQUEST_DENIED")
        )

        with pytest.raises(ValueError, match="Google Places API error"):
            await _search_places("dentist", 40.7128, -74.0060)

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_transport_error_raises_value_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.side_effect = (
            googlemaps.exceptions.TransportError("Connection failed")
        )

        with pytest.raises(
            ValueError, match="Google Places API connection error"
        ):
            await _search_places("dentist", 40.7128, -74.0060)

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    @patch("app.services.provider_search.asyncio.sleep")
    async def test_pagination(self, mock_sleep, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.side_effect = [
            {
                "results": [_make_place(place_id="p1")],
                "next_page_token": "token1",
            },
            {
                "results": [_make_place(place_id="p2")],
                "next_page_token": "token2",
            },
            {
                "results": [_make_place(place_id="p3")],
            },
        ]

        results = await _search_places("dentist", 40.7128, -74.0060)

        assert len(results) == 3
        assert mock_sleep.call_count == 2
        assert mock_client.places_nearby.call_count == 3

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_skips_malformed_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.return_value = {
            "results": [
                _make_place(place_id="valid1"),
                {"name": "Missing place_id"},
                _make_place(place_id="valid2"),
            ],
        }

        results = await _search_places("dentist", 40.7128, -74.0060)

        assert len(results) == 2
        assert results[0].place_id == "valid1"
        assert results[1].place_id == "valid2"

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    @patch("app.services.provider_search.asyncio.sleep")
    async def test_pagination_error_returns_partial(
        self, mock_sleep, mock_get_client
    ):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.side_effect = [
            {
                "results": [_make_place(place_id="p1")],
                "next_page_token": "token1",
            },
            googlemaps.exceptions.ApiError("OVER_QUERY_LIMIT"),
        ]

        results = await _search_places("dentist", 40.7128, -74.0060)

        assert len(results) == 1
        assert results[0].place_id == "p1"


# ============================================================
# search_providers (integrated) Tests
# ============================================================


class TestSearchProvidersIntegrated:
    @pytest.mark.asyncio
    @patch("app.services.provider_search._search_places")
    async def test_without_db_returns_raw_results(self, mock_search):
        """Without db, search_providers returns raw results (no enrichment)."""
        mock_search.return_value = [
            _make_provider_result(place_id="p1"),
        ]

        results = await search_providers(
            "dentist", 40.7128, -74.0060, db=None
        )

        assert len(results) == 1
        assert results[0].phone is None

    @pytest.mark.asyncio
    @patch("app.services.provider_search._search_places")
    async def test_empty_search_returns_empty(self, mock_search):
        mock_search.return_value = []

        results = await search_providers("dentist", 40.7128, -74.0060)

        assert results == []

    @pytest.mark.asyncio
    @patch("app.services.provider_search.get_cached_providers")
    @patch("app.services.provider_search._search_places")
    async def test_with_db_merges_cached_phone(
        self, mock_search, mock_get_cached
    ):
        """Cached phone numbers are merged into results."""
        cached_provider = _make_cached_provider(
            place_id="p1", phone="(555) 111-2222"
        )
        mock_search.return_value = [
            _make_provider_result(place_id="p1"),
        ]
        mock_get_cached.return_value = [cached_provider]

        mock_db = AsyncMock()
        results = await search_providers(
            "dentist", 40.7128, -74.0060, db=mock_db
        )

        assert len(results) == 1
        assert results[0].phone == "(555) 111-2222"

    @pytest.mark.asyncio
    @patch("app.services.provider_search.get_cached_providers")
    @patch("app.services.provider_search._search_places")
    async def test_with_db_uncached_providers_have_no_phone(
        self, mock_search, mock_get_cached
    ):
        """Uncached providers are returned without phone (enrichment deferred)."""
        mock_search.return_value = [
            _make_provider_result(place_id="p1"),
            _make_provider_result(place_id="p2"),
        ]
        mock_get_cached.return_value = []  # Nothing cached

        mock_db = AsyncMock()
        results = await search_providers(
            "dentist", 40.7128, -74.0060, db=mock_db
        )

        assert len(results) == 2
        assert results[0].phone is None
        assert results[1].phone is None

    @pytest.mark.asyncio
    @patch("app.services.provider_search.get_cached_providers")
    @patch("app.services.provider_search._search_places")
    async def test_with_db_mixed_cached_and_uncached(
        self, mock_search, mock_get_cached
    ):
        """Mix of cached and uncached: cached get phone, uncached don't."""
        cached = _make_cached_provider(
            place_id="p1", phone="(555) 111-2222"
        )
        mock_search.return_value = [
            _make_provider_result(place_id="p1"),
            _make_provider_result(place_id="p2"),
        ]
        mock_get_cached.return_value = [cached]

        mock_db = AsyncMock()
        results = await search_providers(
            "dentist", 40.7128, -74.0060, db=mock_db
        )

        assert len(results) == 2
        p1 = next(r for r in results if r.place_id == "p1")
        p2 = next(r for r in results if r.place_id == "p2")
        assert p1.phone == "(555) 111-2222"
        assert p2.phone is None

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_missing_api_key(self, mock_get_client):
        mock_get_client.side_effect = ValueError(
            "GOOGLE_MAPS_API_KEY is not configured"
        )

        with pytest.raises(ValueError, match="GOOGLE_MAPS_API_KEY"):
            await search_providers("dentist", 40.7128, -74.0060)
