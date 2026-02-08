import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models.booking import Booking, BookingStatus
from app.schemas.intent import BookingIntent
from app.services.user_service import DEFAULT_USER_ID


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = DEFAULT_USER_ID
    return user


def _make_booking(**overrides) -> MagicMock:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": DEFAULT_USER_ID,
        "status": BookingStatus.SEARCHING,
        "service_type": "dentist",
        "preferred_date": "2026-02-10",
        "preferred_time": "afternoon",
        "location_override": None,
        "constraints": None,
        "raw_message": "I need a dentist",
        "created_at": datetime(2026, 2, 8),
        "updated_at": datetime(2026, 2, 8),
    }
    defaults.update(overrides)
    booking = MagicMock(spec=Booking)
    for k, v in defaults.items():
        setattr(booking, k, v)
    return booking


async def test_post_bookings_creates_booking(client):
    booking = _make_booking()
    intent = BookingIntent(
        service_type="dentist",
        date="2026-02-10",
        time_preference="afternoon",
        urgency="specific_date",
    )

    with (
        patch(
            "app.routers.bookings.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.bookings.create_booking",
            return_value=(booking, intent),
        ) as mock_create,
    ):
        response = await client.post(
            "/api/bookings",
            json={"message": "I need a dentist next Tuesday afternoon"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["booking_id"] == str(booking.id)
    assert data["status"] == "searching"
    assert data["intent"]["service_type"] == "dentist"
    assert data["intent"]["date"] == "2026-02-10"
    assert data["intent"]["time_preference"] == "afternoon"
    mock_create.assert_awaited_once()


async def test_post_bookings_returns_422_on_empty_message(client):
    response = await client.post(
        "/api/bookings",
        json={"message": ""},
    )
    assert response.status_code == 422


async def test_post_bookings_returns_422_on_missing_message(client):
    response = await client.post(
        "/api/bookings",
        json={},
    )
    assert response.status_code == 422


async def test_post_bookings_returns_422_on_parse_error(client):
    with (
        patch(
            "app.routers.bookings.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.bookings.create_booking",
            side_effect=ValueError("OpenAI API error: connection failed"),
        ),
    ):
        response = await client.post(
            "/api/bookings",
            json={"message": "some input"},
        )

    assert response.status_code == 422
    assert "OpenAI API error" in response.json()["detail"]


async def test_get_booking_returns_booking(client):
    booking = _make_booking()
    with patch(
        "app.routers.bookings.get_booking",
        return_value=booking,
    ):
        response = await client.get(f"/api/bookings/{booking.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(booking.id)
    assert data["status"] == "searching"
    assert data["service_type"] == "dentist"
    assert data["raw_message"] == "I need a dentist"


async def test_get_booking_returns_404_when_not_found(client):
    with patch(
        "app.routers.bookings.get_booking",
        return_value=None,
    ):
        response = await client.get(
            f"/api/bookings/{uuid.uuid4()}"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


async def test_list_bookings_returns_list(client):
    bookings = [_make_booking() for _ in range(3)]
    with (
        patch(
            "app.routers.bookings.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.bookings.list_bookings",
            return_value=bookings,
        ),
    ):
        response = await client.get("/api/bookings")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


async def test_list_bookings_returns_empty_list(client):
    with (
        patch(
            "app.routers.bookings.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.bookings.list_bookings",
            return_value=[],
        ),
    ):
        response = await client.get("/api/bookings")

    assert response.status_code == 200
    assert response.json() == []


async def test_post_bookings_response_has_expected_keys(client):
    booking = _make_booking()
    intent = BookingIntent(service_type="plumber", urgency="asap")

    with (
        patch(
            "app.routers.bookings.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.bookings.create_booking",
            return_value=(booking, intent),
        ),
    ):
        response = await client.post(
            "/api/bookings",
            json={"message": "Plumber ASAP"},
        )

    data = response.json()
    assert set(data.keys()) == {"booking_id", "status", "intent"}
    assert set(data["intent"].keys()) == {
        "service_type",
        "date",
        "time_preference",
        "location_override",
        "constraints",
        "urgency",
    }


async def test_get_shortlist_returns_shortlisted_providers(client):
    from app.schemas.booking import ShortlistItemResponse

    booking = _make_booking()
    shortlist = [
        ShortlistItemResponse(
            rank=1,
            provider_name="Best Dentist",
            provider_phone="(555) 111-2222",
            place_id="p1",
            rating=4.8,
            review_count=200,
            travel_minutes=5.0,
            pre_score=0.92,
            provider_id=uuid.uuid4(),
        ),
        ShortlistItemResponse(
            rank=2,
            provider_name="Good Dentist",
            provider_phone="(555) 333-4444",
            place_id="p2",
            rating=4.5,
            review_count=150,
            travel_minutes=12.0,
            pre_score=0.78,
            provider_id=uuid.uuid4(),
        ),
    ]

    with (
        patch(
            "app.routers.bookings.get_booking",
            return_value=booking,
        ),
        patch(
            "app.routers.bookings.get_shortlist",
            return_value=shortlist,
        ),
    ):
        response = await client.get(
            f"/api/bookings/{booking.id}/shortlist"
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["rank"] == 1
    assert data[0]["provider_name"] == "Best Dentist"
    assert data[0]["pre_score"] == 0.92
    assert data[0]["travel_minutes"] == 5.0
    assert data[0]["rating"] == 4.8
    assert data[1]["rank"] == 2
    assert data[1]["provider_name"] == "Good Dentist"


async def test_get_shortlist_returns_404_when_booking_not_found(client):
    with patch(
        "app.routers.bookings.get_booking",
        return_value=None,
    ):
        response = await client.get(
            f"/api/bookings/{uuid.uuid4()}/shortlist"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


async def test_get_shortlist_returns_empty_when_no_shortlist(client):
    booking = _make_booking()

    with (
        patch(
            "app.routers.bookings.get_booking",
            return_value=booking,
        ),
        patch(
            "app.routers.bookings.get_shortlist",
            return_value=[],
        ),
    ):
        response = await client.get(
            f"/api/bookings/{booking.id}/shortlist"
        )

    assert response.status_code == 200
    assert response.json() == []


async def test_get_shortlist_response_has_expected_keys(client):
    from app.schemas.booking import ShortlistItemResponse

    booking = _make_booking()
    shortlist = [
        ShortlistItemResponse(
            rank=1,
            provider_name="Test",
            provider_phone=None,
            place_id="p1",
            rating=4.0,
            review_count=50,
            travel_minutes=10.0,
            pre_score=0.80,
            provider_id=uuid.uuid4(),
        ),
    ]

    with (
        patch(
            "app.routers.bookings.get_booking",
            return_value=booking,
        ),
        patch(
            "app.routers.bookings.get_shortlist",
            return_value=shortlist,
        ),
    ):
        response = await client.get(
            f"/api/bookings/{booking.id}/shortlist"
        )

    data = response.json()
    assert len(data) == 1
    assert set(data[0].keys()) == {
        "rank",
        "provider_name",
        "provider_phone",
        "place_id",
        "rating",
        "review_count",
        "travel_minutes",
        "pre_score",
        "provider_id",
    }
