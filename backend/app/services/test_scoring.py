from app.services.distance_service import DistanceResult
from app.services.provider_search import ProviderResult
from app.services.scoring import (
    ScoredProvider,
    normalize,
    normalize_inv,
    score_providers,
    user_pref_score,
)


def _make_provider(**overrides) -> ProviderResult:
    """Create a ProviderResult for testing."""
    defaults = {
        "place_id": "place_1",
        "name": "Test Provider",
        "address": "123 Main St",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "rating": 4.0,
        "review_count": 100,
        "is_open": True,
        "phone": "(555) 123-4567",
    }
    defaults.update(overrides)
    return ProviderResult(**defaults)


def _make_distance(**overrides) -> DistanceResult:
    """Create a DistanceResult for testing."""
    defaults = {
        "distance_km": 5.0,
        "duration_minutes": 10.0,
        "status": "ok",
    }
    defaults.update(overrides)
    return DistanceResult(**defaults)


# ============================================================
# normalize Tests
# ============================================================


class TestNormalize:
    def test_midpoint(self):
        assert normalize(3.0, 1.0, 5.0) == 0.5

    def test_min_value(self):
        assert normalize(1.0, 1.0, 5.0) == 0.0

    def test_max_value(self):
        assert normalize(5.0, 1.0, 5.0) == 1.0

    def test_below_min_clamps_to_zero(self):
        assert normalize(0.0, 1.0, 5.0) == 0.0

    def test_above_max_clamps_to_one(self):
        assert normalize(10.0, 1.0, 5.0) == 1.0

    def test_equal_min_max_returns_zero(self):
        assert normalize(5.0, 5.0, 5.0) == 0.0

    def test_inverted_range_returns_zero(self):
        assert normalize(3.0, 5.0, 1.0) == 0.0


# ============================================================
# normalize_inv Tests
# ============================================================


class TestNormalizeInv:
    def test_zero_value_returns_one(self):
        assert normalize_inv(0.0, 60.0) == 1.0

    def test_max_value_returns_zero(self):
        assert normalize_inv(60.0, 60.0) == 0.0

    def test_half_value(self):
        assert normalize_inv(30.0, 60.0) == 0.5

    def test_above_max_clamps_to_zero(self):
        assert normalize_inv(120.0, 60.0) == 0.0

    def test_negative_max_returns_zero(self):
        assert normalize_inv(10.0, 0.0) == 0.0

    def test_infinity_returns_zero(self):
        assert normalize_inv(float("inf"), 60.0) == 0.0


# ============================================================
# user_pref_score Tests
# ============================================================


class TestUserPrefScore:
    def test_preferred_provider_returns_one(self):
        provider = _make_provider(place_id="fav_1", rating=4.5)
        score = user_pref_score(provider, ["fav_1"], min_rating=4.0)
        assert score == 1.0

    def test_below_min_rating_returns_negative(self):
        provider = _make_provider(place_id="low", rating=3.0)
        score = user_pref_score(provider, [], min_rating=4.0)
        assert score == -0.5

    def test_normal_provider_returns_zero(self):
        provider = _make_provider(place_id="normal", rating=4.5)
        score = user_pref_score(provider, [], min_rating=4.0)
        assert score == 0.0

    def test_preferred_overrides_low_rating(self):
        """A favorite provider should score 1.0 even if below min_rating."""
        provider = _make_provider(place_id="fav_low", rating=2.0)
        score = user_pref_score(provider, ["fav_low"], min_rating=4.0)
        assert score == 1.0

    def test_empty_preferred_list(self):
        provider = _make_provider(place_id="any", rating=4.5)
        score = user_pref_score(provider, [], min_rating=0.0)
        assert score == 0.0


# ============================================================
# score_providers Tests
# ============================================================


class TestScoreProviders:
    def test_higher_rating_scores_higher(self):
        """Provider with 5.0 rating scores higher than 3.0 (all else equal)."""
        providers = [
            _make_provider(place_id="high", rating=5.0),
            _make_provider(place_id="low", rating=3.0),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=10.0),
        ]

        result = score_providers(providers, distances)

        assert result[0].provider.place_id == "high"
        assert result[1].provider.place_id == "low"
        assert result[0].score > result[1].score

    def test_closer_provider_scores_higher(self):
        """Closer provider scores higher than distant one (all else equal)."""
        providers = [
            _make_provider(place_id="far", rating=4.0),
            _make_provider(place_id="close", rating=4.0),
        ]
        distances = [
            _make_distance(duration_minutes=50.0),
            _make_distance(duration_minutes=5.0),
        ]

        result = score_providers(providers, distances)

        assert result[0].provider.place_id == "close"
        assert result[1].provider.place_id == "far"

    def test_blocked_provider_excluded(self):
        """Blocked providers should not appear in results."""
        providers = [
            _make_provider(place_id="good", rating=4.5),
            _make_provider(place_id="blocked_1", rating=5.0),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=5.0),
        ]

        result = score_providers(
            providers, distances, blocked_providers=["blocked_1"]
        )

        assert len(result) == 1
        assert result[0].provider.place_id == "good"

    def test_favorite_provider_gets_boost(self):
        """Preferred provider should score higher than equal non-preferred."""
        providers = [
            _make_provider(place_id="normal", rating=4.5),
            _make_provider(place_id="fav", rating=4.5),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=10.0),
        ]

        result = score_providers(
            providers, distances, preferred_providers=["fav"]
        )

        assert result[0].provider.place_id == "fav"
        assert result[0].score > result[1].score

    def test_below_min_rating_penalized(self):
        """Provider below min_rating should score lower."""
        providers = [
            _make_provider(place_id="good", rating=4.5),
            _make_provider(place_id="bad", rating=3.0),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=10.0),
        ]

        result = score_providers(
            providers, distances, min_rating=4.0
        )

        assert result[0].provider.place_id == "good"
        assert result[0].score > result[1].score

    def test_top_n_limits_results(self):
        """Only top N providers should be returned."""
        providers = [
            _make_provider(place_id=f"p{i}", rating=4.0)
            for i in range(20)
        ]
        distances = [
            _make_distance(duration_minutes=10.0)
            for _ in range(20)
        ]

        result = score_providers(providers, distances, top_n=15)

        assert len(result) == 15

    def test_custom_top_n(self):
        """Custom top_n value should be respected."""
        providers = [
            _make_provider(place_id=f"p{i}", rating=4.0)
            for i in range(10)
        ]
        distances = [
            _make_distance(duration_minutes=10.0)
            for _ in range(10)
        ]

        result = score_providers(providers, distances, top_n=5)

        assert len(result) == 5

    def test_fewer_than_top_n_returns_all(self):
        """When fewer providers than top_n, return all."""
        providers = [
            _make_provider(place_id="p1", rating=4.0),
            _make_provider(place_id="p2", rating=4.5),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=15.0),
        ]

        result = score_providers(providers, distances, top_n=15)

        assert len(result) == 2

    def test_empty_providers_returns_empty(self):
        result = score_providers([], [])
        assert result == []

    def test_open_provider_scores_higher(self):
        """Open provider should score higher than closed (all else equal)."""
        providers = [
            _make_provider(place_id="closed", rating=4.0, is_open=False),
            _make_provider(place_id="open", rating=4.0, is_open=True),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=10.0),
        ]

        result = score_providers(providers, distances)

        assert result[0].provider.place_id == "open"
        assert result[0].score > result[1].score

    def test_is_open_none_treated_as_closed(self):
        """Provider with is_open=None should not get the open bonus."""
        providers = [
            _make_provider(place_id="unknown", rating=4.0, is_open=None),
            _make_provider(place_id="open", rating=4.0, is_open=True),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=10.0),
        ]

        result = score_providers(providers, distances)

        assert result[0].provider.place_id == "open"

    def test_zero_reviews_handled(self):
        """Provider with 0 reviews should not cause errors."""
        providers = [_make_provider(place_id="p1", review_count=0)]
        distances = [_make_distance(duration_minutes=10.0)]

        result = score_providers(providers, distances)

        assert len(result) == 1
        assert result[0].score > 0

    def test_infinity_distance_scores_lowest(self):
        """Unreachable provider (inf distance) should score low for distance."""
        providers = [
            _make_provider(place_id="near", rating=4.0),
            _make_provider(place_id="unreachable", rating=4.0),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(
                duration_minutes=float("inf"), status="zero_results"
            ),
        ]

        result = score_providers(providers, distances)

        assert result[0].provider.place_id == "near"
        assert result[0].score > result[1].score

    def test_missing_distance_uses_fallback(self):
        """If distances list is shorter than providers, use fallback."""
        providers = [
            _make_provider(place_id="p1", rating=4.0),
            _make_provider(place_id="p2", rating=4.0),
        ]
        distances = [_make_distance(duration_minutes=10.0)]

        result = score_providers(providers, distances)

        assert len(result) == 2
        # p1 has real distance, p2 gets inf fallback → p1 scores higher
        assert result[0].provider.place_id == "p1"

    def test_travel_minutes_in_result(self):
        """ScoredProvider should contain travel_minutes from distance."""
        providers = [_make_provider(place_id="p1")]
        distances = [_make_distance(duration_minutes=12.5)]

        result = score_providers(providers, distances)

        assert result[0].travel_minutes == 12.5

    def test_all_blocked_returns_empty(self):
        """If all providers are blocked, return empty list."""
        providers = [
            _make_provider(place_id="b1"),
            _make_provider(place_id="b2"),
        ]
        distances = [
            _make_distance(duration_minutes=10.0),
            _make_distance(duration_minutes=10.0),
        ]

        result = score_providers(
            providers, distances, blocked_providers=["b1", "b2"]
        )

        assert result == []

    def test_scored_provider_model(self):
        """ScoredProvider should contain provider, score, travel_minutes."""
        sp = ScoredProvider(
            provider=_make_provider(),
            score=0.85,
            travel_minutes=10.0,
        )
        assert sp.score == 0.85
        assert sp.travel_minutes == 10.0
        assert sp.provider.place_id == "place_1"
