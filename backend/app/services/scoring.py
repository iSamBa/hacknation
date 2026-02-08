import logging

from pydantic import BaseModel

from app.services.distance_service import DistanceResult
from app.services.provider_search import ProviderResult

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 15

# Scoring weights
W_RATING = 0.30
W_DISTANCE = 0.25
W_REVIEWS = 0.15
W_USER_PREF = 0.20
W_OPEN_HOURS = 0.10

# Normalization bounds
MAX_TRAVEL_MINUTES = 60
MAX_REVIEW_COUNT = 500
MIN_RATING_SCALE = 1.0
MAX_RATING_SCALE = 5.0


class ScoredProvider(BaseModel):
    """A provider with its computed score and travel time."""

    provider: ProviderResult
    score: float
    travel_minutes: float


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to a 0-1 scale.

    Values below min_val clamp to 0, above max_val clamp to 1.
    """
    if max_val <= min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def normalize_inv(value: float, max_val: float) -> float:
    """Inverse normalize: lower values score higher (0-1 scale).

    Used for distance/time where closer is better.
    Values at or below 0 return 1.0, values at or above max_val return 0.0.
    """
    if max_val <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - value / max_val))


def user_pref_score(
    provider: ProviderResult,
    preferred_providers: list[str],
    min_rating: float,
) -> float:
    """Calculate user preference score for a provider.

    Args:
        provider: The provider to evaluate.
        preferred_providers: List of preferred place_ids.
        min_rating: User's minimum acceptable rating.

    Returns:
        Preference score: 1.0 for favorites, -0.5 if below min_rating,
        0.0 otherwise.
    """
    if provider.place_id in preferred_providers:
        return 1.0
    if provider.rating < min_rating:
        return -0.5
    return 0.0


def score_providers(
    providers: list[ProviderResult],
    distances: list[DistanceResult],
    blocked_providers: list[str] | None = None,
    preferred_providers: list[str] | None = None,
    min_rating: float = 0.0,
    top_n: int = DEFAULT_TOP_N,
) -> list[ScoredProvider]:
    """Score and rank providers based on quality, proximity, and preferences.

    Args:
        providers: List of providers to score.
        distances: Matching list of distance results (same order as providers).
        blocked_providers: Place IDs to exclude entirely.
        preferred_providers: Place IDs that get a score boost.
        min_rating: User's minimum acceptable rating (providers below are penalized).
        top_n: Number of top providers to return.

    Returns:
        Top N providers sorted by score descending.
    """
    if not providers:
        return []

    blocked = set(blocked_providers or [])
    preferred = preferred_providers or []
    scored: list[ScoredProvider] = []

    for i, provider in enumerate(providers):
        if provider.place_id in blocked:
            continue

        distance = distances[i] if i < len(distances) else DistanceResult(
            distance_km=float("inf"),
            duration_minutes=float("inf"),
            status="error",
        )

        pref = user_pref_score(provider, preferred, min_rating)

        score = (
            normalize(provider.rating, MIN_RATING_SCALE, MAX_RATING_SCALE)
            * W_RATING
            + normalize_inv(distance.duration_minutes, MAX_TRAVEL_MINUTES)
            * W_DISTANCE
            + normalize(provider.review_count, 0, MAX_REVIEW_COUNT)
            * W_REVIEWS
            + pref * W_USER_PREF
            + (W_OPEN_HOURS if provider.is_open is True else 0.0)
        )

        scored.append(
            ScoredProvider(
                provider=provider,
                score=round(score, 4),
                travel_minutes=round(distance.duration_minutes, 2),
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_n]
