import asyncio
import logging
from datetime import datetime, timedelta, timezone

import googlemaps
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.provider import Provider

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 7

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
    phone: str | None = None


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


def _provider_to_result(provider: Provider) -> ProviderResult:
    """Convert a cached Provider model to a ProviderResult."""
    return ProviderResult(
        place_id=provider.place_id,
        name=provider.name,
        address=provider.address,
        latitude=provider.latitude,
        longitude=provider.longitude,
        rating=provider.rating,
        review_count=provider.review_count,
        is_open=provider.is_open,
        phone=provider.phone,
    )


async def enrich_with_phone(
    providers: list[ProviderResult],
) -> list[ProviderResult]:
    """Fetch phone numbers for providers via Google Place Details API.

    Filters out providers that don't have a phone number.

    Args:
        providers: List of ProviderResult from Places Nearby Search.

    Returns:
        List of ProviderResult with phone numbers set, excluding
        providers without phone numbers.
    """
    client = _get_client()
    enriched: list[ProviderResult] = []

    for provider in providers:
        try:
            details = await asyncio.to_thread(
                client.place,
                provider.place_id,
                fields=["formatted_phone_number"],
            )
        except (
            googlemaps.exceptions.ApiError,
            googlemaps.exceptions.TransportError,
        ) as e:
            logger.warning(
                "Failed to fetch details for %s: %s",
                provider.place_id,
                e,
            )
            continue

        phone = details.get("result", {}).get("formatted_phone_number")
        if phone:
            enriched.append(provider.model_copy(update={"phone": phone}))
        else:
            logger.debug(
                "No phone number for %s (%s), skipping",
                provider.name,
                provider.place_id,
            )

    return enriched


async def get_cached_providers(
    db: AsyncSession, place_ids: list[str]
) -> list[Provider]:
    """Get cached providers that are still fresh (< CACHE_TTL_DAYS days old).

    Args:
        db: Database session.
        place_ids: List of Google Place IDs to look up.

    Returns:
        List of cached Provider models with fresh cache entries.
    """
    if not place_ids:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)
    result = await db.execute(
        select(Provider).where(
            Provider.place_id.in_(place_ids),
            Provider.cached_at >= cutoff,
            Provider.phone.is_not(None),
        )
    )
    return list(result.scalars().all())


async def cache_providers(
    db: AsyncSession, providers: list[ProviderResult]
) -> None:
    """Upsert providers into the database cache.

    Updates existing entries if found, creates new ones otherwise.
    Uses bulk query to fetch existing providers and handles race conditions.

    Args:
        db: Database session.
        providers: List of ProviderResult to cache (should have phone set).
    """
    if not providers:
        return

    # Bulk fetch existing providers in one query
    place_ids = [p.place_id for p in providers]
    result = await db.execute(
        select(Provider).where(Provider.place_id.in_(place_ids))
    )
    existing_map = {p.place_id: p for p in result.scalars().all()}

    now = datetime.now(timezone.utc)
    for provider in providers:
        existing = existing_map.get(provider.place_id)

        if existing:
            existing.name = provider.name
            existing.address = provider.address
            existing.latitude = provider.latitude
            existing.longitude = provider.longitude
            existing.phone = provider.phone
            existing.rating = provider.rating
            existing.review_count = provider.review_count
            existing.is_open = provider.is_open
            existing.cached_at = now
        else:
            db.add(
                Provider(
                    place_id=provider.place_id,
                    name=provider.name,
                    address=provider.address,
                    latitude=provider.latitude,
                    longitude=provider.longitude,
                    phone=provider.phone,
                    rating=provider.rating,
                    review_count=provider.review_count,
                    is_open=provider.is_open,
                    cached_at=now,
                )
            )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.warning("Race condition during provider caching, retried")


async def _search_places(
    service_type: str,
    lat: float,
    lng: float,
    radius_km: float = 10.0,
) -> list[ProviderResult]:
    """Search Google Places Nearby for providers.

    This is the raw API search without caching or enrichment.
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


async def search_providers(
    service_type: str,
    lat: float,
    lng: float,
    radius_km: float = 10.0,
    db: AsyncSession | None = None,
) -> list[ProviderResult]:
    """Search for providers near a location by service type.

    When a database session is provided, checks cache first and only
    fetches from Google API for uncached/stale providers. Results are
    enriched with phone numbers and cached.

    When no database session is provided, performs a raw search without
    caching (backward-compatible with Story 001).

    Args:
        service_type: Type of service to search for (e.g. "dentist").
        lat: Latitude of the search center.
        lng: Longitude of the search center.
        radius_km: Search radius in kilometers (default 10).
        db: Optional database session for caching.

    Returns:
        List of ProviderResult objects with phone numbers.

    Raises:
        ValueError: If the API key is missing or the API returns an error.
    """
    # Step 1: Search Google Places for nearby providers
    all_providers = await _search_places(service_type, lat, lng, radius_km)

    if not all_providers:
        return []

    # Without DB, just enrich and return (no caching)
    if db is None:
        return await enrich_with_phone(all_providers)

    # Step 2: Check which providers are already cached and fresh
    place_ids = [p.place_id for p in all_providers]
    cached = await get_cached_providers(db, place_ids)
    cached_ids = {p.place_id for p in cached}

    # Step 3: Identify uncached/stale providers needing enrichment
    uncached = [p for p in all_providers if p.place_id not in cached_ids]

    # Step 4: Enrich uncached providers with phone numbers
    newly_enriched: list[ProviderResult] = []
    if uncached:
        newly_enriched = await enrich_with_phone(uncached)
        # Cache the newly enriched providers
        if newly_enriched:
            await cache_providers(db, newly_enriched)

    # Step 5: Combine cached + newly enriched results
    results = [_provider_to_result(p) for p in cached]
    results.extend(newly_enriched)

    return results
