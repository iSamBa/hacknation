from unittest.mock import MagicMock, patch

import googlemaps.exceptions
import pytest

from app.services.distance_service import (
    DistanceResult,
    _parse_elements,
    calculate_distances,
)


def _make_ok_element(distance_m: int = 5000, duration_s: int = 600) -> dict:
    """Create a Distance Matrix element with status OK."""
    return {
        "status": "OK",
        "distance": {"value": distance_m, "text": f"{distance_m / 1000} km"},
        "duration": {"value": duration_s, "text": f"{duration_s // 60} mins"},
    }


def _make_error_element(status: str = "ZERO_RESULTS") -> dict:
    """Create a Distance Matrix element with an error status."""
    return {"status": status}


# ============================================================
# DistanceResult Schema Tests
# ============================================================


class TestDistanceResult:
    def test_valid_result(self):
        result = DistanceResult(
            distance_km=5.0, duration_minutes=10.0, status="ok"
        )
        assert result.distance_km == 5.0
        assert result.duration_minutes == 10.0
        assert result.status == "ok"

    def test_infinity_values(self):
        result = DistanceResult(
            distance_km=float("inf"),
            duration_minutes=float("inf"),
            status="zero_results",
        )
        assert result.distance_km == float("inf")
        assert result.duration_minutes == float("inf")


# ============================================================
# _parse_elements Tests
# ============================================================


class TestParseElements:
    def test_parses_ok_elements(self):
        elements = [
            _make_ok_element(10000, 1200),
            _make_ok_element(3000, 300),
        ]
        results = _parse_elements(elements)

        assert len(results) == 2
        assert results[0].distance_km == 10.0
        assert results[0].duration_minutes == 20.0
        assert results[0].status == "ok"
        assert results[1].distance_km == 3.0
        assert results[1].duration_minutes == 5.0

    def test_parses_error_elements(self):
        elements = [_make_error_element("ZERO_RESULTS")]
        results = _parse_elements(elements)

        assert len(results) == 1
        assert results[0].distance_km == float("inf")
        assert results[0].duration_minutes == float("inf")
        assert results[0].status == "zero_results"

    def test_mixed_ok_and_error(self):
        elements = [
            _make_ok_element(5000, 600),
            _make_error_element("NOT_FOUND"),
            _make_ok_element(8000, 900),
        ]
        results = _parse_elements(elements)

        assert len(results) == 3
        assert results[0].status == "ok"
        assert results[1].status == "not_found"
        assert results[1].distance_km == float("inf")
        assert results[2].status == "ok"

    def test_empty_elements(self):
        results = _parse_elements([])
        assert results == []

    def test_malformed_ok_element(self):
        elements = [{"status": "OK"}]  # Missing distance/duration keys
        results = _parse_elements(elements)

        assert len(results) == 1
        assert results[0].status == "error"
        assert results[0].distance_km == float("inf")


# ============================================================
# calculate_distances Tests
# ============================================================


class TestCalculateDistances:
    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_returns_distances(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.return_value = {
            "rows": [
                {
                    "elements": [
                        _make_ok_element(5000, 600),
                        _make_ok_element(12000, 1500),
                    ]
                }
            ]
        }

        results = await calculate_distances(
            origin=(40.7128, -74.0060),
            destinations=[(40.73, -73.99), (40.75, -73.98)],
        )

        assert len(results) == 2
        assert results[0].distance_km == 5.0
        assert results[0].duration_minutes == 10.0
        assert results[1].distance_km == 12.0
        assert results[1].duration_minutes == 25.0
        mock_client.distance_matrix.assert_called_once_with(
            origins=[(40.7128, -74.0060)],
            destinations=[(40.73, -73.99), (40.75, -73.98)],
            mode="driving",
        )

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_empty_destinations(self, mock_get_client):
        results = await calculate_distances(
            origin=(40.7128, -74.0060),
            destinations=[],
        )
        assert results == []
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_unreachable_destination(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.return_value = {
            "rows": [
                {
                    "elements": [
                        _make_ok_element(5000, 600),
                        _make_error_element("ZERO_RESULTS"),
                    ]
                }
            ]
        }

        results = await calculate_distances(
            origin=(40.7128, -74.0060),
            destinations=[(40.73, -73.99), (0.0, 0.0)],
        )

        assert len(results) == 2
        assert results[0].status == "ok"
        assert results[1].status == "zero_results"
        assert results[1].distance_km == float("inf")
        assert results[1].duration_minutes == float("inf")

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_api_error_raises_value_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.side_effect = (
            googlemaps.exceptions.ApiError("REQUEST_DENIED")
        )

        with pytest.raises(
            ValueError, match="Google Distance Matrix API error"
        ):
            await calculate_distances(
                origin=(40.7128, -74.0060),
                destinations=[(40.73, -73.99)],
            )

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_transport_error_raises_value_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.side_effect = (
            googlemaps.exceptions.TransportError("Connection failed")
        )

        with pytest.raises(
            ValueError, match="Google Distance Matrix API connection error"
        ):
            await calculate_distances(
                origin=(40.7128, -74.0060),
                destinations=[(40.73, -73.99)],
            )

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_no_rows_raises_value_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.return_value = {"rows": []}

        with pytest.raises(
            ValueError, match="returned no rows"
        ):
            await calculate_distances(
                origin=(40.7128, -74.0060),
                destinations=[(40.73, -73.99)],
            )

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_missing_elements_raises_value_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.return_value = {
            "rows": [{}]  # Missing "elements" key
        }

        with pytest.raises(ValueError, match="returned no elements"):
            await calculate_distances(
                origin=(40.7128, -74.0060),
                destinations=[(40.73, -73.99)],
            )

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_batch_splits_over_25_destinations(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First batch: 25 elements, second batch: 5 elements
        mock_client.distance_matrix.side_effect = [
            {
                "rows": [
                    {
                        "elements": [
                            _make_ok_element(i * 1000, i * 100)
                            for i in range(25)
                        ]
                    }
                ]
            },
            {
                "rows": [
                    {
                        "elements": [
                            _make_ok_element(i * 1000, i * 100)
                            for i in range(25, 30)
                        ]
                    }
                ]
            },
        ]

        destinations = [(40.0 + i * 0.01, -74.0) for i in range(30)]
        results = await calculate_distances(
            origin=(40.7128, -74.0060),
            destinations=destinations,
        )

        assert len(results) == 30
        assert mock_client.distance_matrix.call_count == 2

        # Verify first call had 25 destinations
        first_call = mock_client.distance_matrix.call_args_list[0]
        assert len(first_call.kwargs["destinations"]) == 25

        # Verify second call had 5 destinations
        second_call = mock_client.distance_matrix.call_args_list[1]
        assert len(second_call.kwargs["destinations"]) == 5

    @pytest.mark.asyncio
    @patch("app.services.distance_service._get_client")
    async def test_exactly_25_destinations_single_call(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.distance_matrix.return_value = {
            "rows": [
                {
                    "elements": [
                        _make_ok_element(1000, 120) for _ in range(25)
                    ]
                }
            ]
        }

        destinations = [(40.0 + i * 0.01, -74.0) for i in range(25)]
        results = await calculate_distances(
            origin=(40.7128, -74.0060),
            destinations=destinations,
        )

        assert len(results) == 25
        assert mock_client.distance_matrix.call_count == 1
