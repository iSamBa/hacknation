import asyncio
import logging

import googlemaps
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

_client: googlemaps.Client | None = None


def _get_client() -> googlemaps.Client:
    """Lazily initialize the Google Maps client."""
    global _client
    if _client is None:
        if not settings.GOOGLE_MAPS_API_KEY:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY is not configured. "
                "Set it in your environment or .env file."
            )
        _client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    return _client


class ProviderResult(BaseModel):
    """A provider found via Google Places Nearby Search."""

    place_id: str
    name: str
    address: str = ""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    is_open: bool | None = None


def _parse_place(place: dict) -> ProviderResult | None:
    """Parse a single Google Places result into a ProviderResult.

    Returns None if the place data is malformed.
    """
    try:
        return ProviderResult(
            place_id=place["place_id"],
            name=place["name"],
            address=place.get("vicinity", ""),
            latitude=place["geometry"]["location"]["lat"],
            longitude=place["geometry"]["location"]["lng"],
            rating=place.get("rating", 0.0),
            review_count=place.get("user_ratings_total", 0),
            is_open=place.get("opening_hours", {}).get("open_now"),
        )
    except (KeyError, TypeError) as e:
        logger.warning("Skipping malformed place result: %s", e)
        return None


async def search_providers(
    service_type: str,
    lat: float,
    lng: float,
    radius_km: float = 10.0,
) -> list[ProviderResult]:
    """Search for providers near a location by service type.

    Uses Google Places Nearby Search API. Handles pagination to fetch
    up to 60 results (3 pages of 20).

    Args:
        service_type: Type of service to search for (e.g. "dentist").
        lat: Latitude of the search center.
        lng: Longitude of the search center.
        radius_km: Search radius in kilometers (default 10).

    Returns:
        List of ProviderResult objects.

    Raises:
        ValueError: If the API key is missing or the API returns an error.
    """
    client = _get_client()
    radius_m = int(radius_km * 1000)

    try:
        response = await asyncio.to_thread(
            client.places_nearby,
            location=(lat, lng),
            radius=radius_m,
            keyword=service_type,
        )
    except googlemaps.exceptions.ApiError as e:
        raise ValueError(f"Google Places API error: {e}") from e
    except googlemaps.exceptions.TransportError as e:
        raise ValueError(f"Google Places API connection error: {e}") from e

    providers: list[ProviderResult] = []

    for place in response.get("results", []):
        result = _parse_place(place)
        if result is not None:
            providers.append(result)

    # Handle pagination (up to 3 pages total)
    pages_fetched = 1
    while "next_page_token" in response and pages_fetched < 3:
        # Google requires a short delay before using next_page_token
        await asyncio.sleep(2)
        try:
            response = await asyncio.to_thread(
                client.places_nearby,
                page_token=response["next_page_token"],
            )
        except (
            googlemaps.exceptions.ApiError,
            googlemaps.exceptions.TransportError,
        ) as e:
            logger.warning(
                "Pagination failed on page %d: %s", pages_fetched + 1, e
            )
            break

        for place in response.get("results", []):
            result = _parse_place(place)
            if result is not None:
                providers.append(result)

        pages_fetched += 1

    return providers
