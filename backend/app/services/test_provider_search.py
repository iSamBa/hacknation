from unittest.mock import MagicMock, patch

import googlemaps.exceptions
import pytest

from app.services.provider_search import (
    ProviderResult,
    _parse_place,
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


class TestSearchProviders:
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

        results = await search_providers("dentist", 40.7128, -74.0060, 10.0)

        assert len(results) == 2
        assert results[0].place_id == "place1"
        assert results[0].name == "Dentist A"
        assert results[1].place_id == "place2"

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_empty_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.return_value = {"results": []}

        results = await search_providers("obscure_service", 40.7128, -74.0060)

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
            await search_providers("dentist", 40.7128, -74.0060)

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
            await search_providers("dentist", 40.7128, -74.0060)

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

        results = await search_providers("dentist", 40.7128, -74.0060)

        assert len(results) == 3
        assert results[0].place_id == "p1"
        assert results[1].place_id == "p2"
        assert results[2].place_id == "p3"
        assert mock_sleep.call_count == 2
        assert mock_client.places_nearby.call_count == 3

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_missing_api_key(self, mock_get_client):
        mock_get_client.side_effect = ValueError(
            "GOOGLE_MAPS_API_KEY is not configured"
        )

        with pytest.raises(ValueError, match="GOOGLE_MAPS_API_KEY"):
            await search_providers("dentist", 40.7128, -74.0060)

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_default_radius(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.places_nearby.return_value = {"results": []}

        await search_providers("dentist", 40.7128, -74.0060)

        mock_client.places_nearby.assert_called_once()

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

        results = await search_providers("dentist", 40.7128, -74.0060)

        assert len(results) == 2
        assert results[0].place_id == "valid1"
        assert results[1].place_id == "valid2"

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    @patch("app.services.provider_search.asyncio.sleep")
    async def test_pagination_error_returns_partial_results(
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

        results = await search_providers("dentist", 40.7128, -74.0060)

        assert len(results) == 1
        assert results[0].place_id == "p1"
