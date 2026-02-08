import asyncio
import logging

import googlemaps.exceptions
from pydantic import BaseModel

from app.services.provider_search import _get_client

logger = logging.getLogger(__name__)

MAX_DESTINATIONS_PER_CALL = 25


class DistanceResult(BaseModel):
    """Result of a distance calculation for a single destination."""

    distance_km: float
    duration_minutes: float
    status: str


def _parse_elements(elements: list[dict]) -> list[DistanceResult]:
    """Parse Distance Matrix response elements into DistanceResult objects."""
    results: list[DistanceResult] = []
    for element in elements:
        try:
            if element["status"] == "OK":
                results.append(
                    DistanceResult(
                        distance_km=element["distance"]["value"] / 1000,
                        duration_minutes=element["duration"]["value"] / 60,
                        status="ok",
                    )
                )
            else:
                results.append(
                    DistanceResult(
                        distance_km=float("inf"),
                        duration_minutes=float("inf"),
                        status=element["status"].lower(),
                    )
                )
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed distance element: %s", e)
            results.append(
                DistanceResult(
                    distance_km=float("inf"),
                    duration_minutes=float("inf"),
                    status="error",
                )
            )
    return results


async def calculate_distances(
    origin: tuple[float, float],
    destinations: list[tuple[float, float]],
    mode: str = "driving",
) -> list[DistanceResult]:
    """Calculate driving distances and durations from origin to destinations.

    Uses Google Distance Matrix API. Batches requests in chunks of 25
    destinations (API limit per call).

    Args:
        origin: (latitude, longitude) of the starting point.
        destinations: List of (latitude, longitude) for each destination.

    Returns:
        List of DistanceResult, one per destination in the same order.

    Raises:
        ValueError: If the API key is missing or the API returns an error.
    """
    if not destinations:
        return []

    client = _get_client()
    all_results: list[DistanceResult] = []

    for i in range(0, len(destinations), MAX_DESTINATIONS_PER_CALL):
        batch = destinations[i : i + MAX_DESTINATIONS_PER_CALL]

        try:
            response = await asyncio.to_thread(
                client.distance_matrix,
                origins=[origin],
                destinations=batch,
                mode=mode,
            )
        except googlemaps.exceptions.ApiError as e:
            raise ValueError(
                f"Google Distance Matrix API error: {e}"
            ) from e
        except googlemaps.exceptions.TransportError as e:
            raise ValueError(
                f"Google Distance Matrix API connection error: {e}"
            ) from e

        rows = response.get("rows", [])
        if not rows:
            raise ValueError(
                "Google Distance Matrix API returned no rows"
            )

        elements = rows[0].get("elements")
        if elements is None:
            raise ValueError(
                "Google Distance Matrix API returned no elements"
            )

        all_results.extend(_parse_elements(elements))

    return all_results
