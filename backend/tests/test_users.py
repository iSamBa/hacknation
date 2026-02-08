from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models.user import UserProfile
from app.services.user_service import DEFAULT_USER_ID


def _make_user(**overrides) -> MagicMock:
    defaults = {
        "id": DEFAULT_USER_ID,
        "name": "Default User",
        "phone": None,
        "email": None,
        "address": "",
        "latitude": 0.0,
        "longitude": 0.0,
        "preferred_times": [],
        "preferred_days": [],
        "avoid_times": None,
        "max_distance_km": 10.0,
        "min_rating": 4.0,
        "shortlist_count": 15,
        "preferred_providers": [],
        "blocked_providers": [],
        "language_preference": "english",
        "transport_mode": "driving",
        "google_calendar_id": None,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    user = MagicMock(spec=UserProfile)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


async def test_get_me_creates_default_user(client):
    user = _make_user()
    with patch(
        "app.routers.users.get_or_create_default_user", return_value=user
    ) as mock_get:
        response = await client.get("/api/users/me")
        assert response.status_code == 200
        mock_get.assert_awaited_once()
        data = response.json()
        assert data["id"] == str(DEFAULT_USER_ID)
        assert data["name"] == "Default User"


async def test_get_me_returns_all_fields(client):
    user = _make_user(
        name="Test User",
        email="test@example.com",
        phone="+1234567890",
        address="123 Main St",
        latitude=48.8566,
        longitude=2.3522,
        preferred_times=["09:00", "10:00"],
        preferred_days=["Mon", "Tue"],
        max_distance_km=15.0,
        min_rating=3.5,
        language_preference="french",
    )
    with patch(
        "app.routers.users.get_or_create_default_user", return_value=user
    ):
        response = await client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["phone"] == "+1234567890"
        assert data["address"] == "123 Main St"
        assert data["latitude"] == 48.8566
        assert data["longitude"] == 2.3522
        assert data["preferred_times"] == ["09:00", "10:00"]
        assert data["preferred_days"] == ["Mon", "Tue"]
        assert data["max_distance_km"] == 15.0
        assert data["min_rating"] == 3.5
        assert data["shortlist_count"] == 15
        assert data["language_preference"] == "french"
        assert "created_at" in data
        assert "updated_at" in data


async def test_put_me_updates_fields(client):
    updated_user = _make_user(name="Updated Name", address="456 Oak Ave")
    with (
        patch(
            "app.routers.users.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.users.update_user_profile", return_value=updated_user
        ) as mock_update,
    ):
        response = await client.put(
            "/api/users/me",
            json={"name": "Updated Name", "address": "456 Oak Ave"},
        )
        assert response.status_code == 200
        mock_update.assert_awaited_once()
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["address"] == "456 Oak Ave"


async def test_put_me_partial_update(client):
    updated_user = _make_user(name="Only Name Changed")
    with (
        patch(
            "app.routers.users.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.users.update_user_profile", return_value=updated_user
        ),
    ):
        response = await client.put(
            "/api/users/me",
            json={"name": "Only Name Changed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Only Name Changed"
        assert data["address"] == ""


async def test_put_me_validates_latitude_range(client):
    response = await client.put(
        "/api/users/me",
        json={"latitude": 100.0},
    )
    assert response.status_code == 422


async def test_put_me_validates_longitude_range(client):
    response = await client.put(
        "/api/users/me",
        json={"longitude": 200.0},
    )
    assert response.status_code == 422


async def test_put_me_validates_min_rating_range(client):
    response = await client.put(
        "/api/users/me",
        json={"min_rating": 6.0},
    )
    assert response.status_code == 422


async def test_put_me_validates_max_distance_positive(client):
    response = await client.put(
        "/api/users/me",
        json={"max_distance_km": -5.0},
    )
    assert response.status_code == 422


async def test_get_me_response_matches_schema(client):
    user = _make_user()
    with patch(
        "app.routers.users.get_or_create_default_user", return_value=user
    ):
        response = await client.get("/api/users/me")
        data = response.json()
        expected_keys = {
            "id",
            "name",
            "phone",
            "email",
            "address",
            "latitude",
            "longitude",
            "preferred_times",
            "preferred_days",
            "avoid_times",
            "max_distance_km",
            "min_rating",
            "shortlist_count",
            "preferred_providers",
            "blocked_providers",
            "language_preference",
            "transport_mode",
            "google_calendar_id",
            "created_at",
            "updated_at",
        }
        assert set(data.keys()) == expected_keys


async def test_put_me_empty_body_succeeds(client):
    user = _make_user()
    with (
        patch(
            "app.routers.users.get_or_create_default_user",
            return_value=user,
        ),
        patch(
            "app.routers.users.update_user_profile", return_value=user
        ),
    ):
        response = await client.put("/api/users/me", json={})
        assert response.status_code == 200


async def test_put_me_validates_shortlist_count_too_low(client):
    response = await client.put(
        "/api/users/me",
        json={"shortlist_count": 0},
    )
    assert response.status_code == 422


async def test_put_me_validates_shortlist_count_too_high(client):
    response = await client.put(
        "/api/users/me",
        json={"shortlist_count": 51},
    )
    assert response.status_code == 422
