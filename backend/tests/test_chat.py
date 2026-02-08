import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models.booking import Booking, BookingStatus
from app.schemas.intent import ChatResponse
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


async def test_chat_greeting_returns_conversational_reply(client):
    chat_response = ChatResponse(
        is_booking_request=False,
        reply="Hello! How can I help you book an appointment?",
    )

    with (
        patch(
            "app.routers.chat.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.chat.classify_and_parse",
            return_value=chat_response,
        ),
    ):
        response = await client.post(
            "/api/chat",
            json={"message": "hi"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["is_booking_request"] is False
    assert data["reply"] == "Hello! How can I help you book an appointment?"
    assert data["booking_id"] is None
    assert data["intent"] is None


async def test_chat_booking_request_creates_booking(client):
    chat_response = ChatResponse(
        is_booking_request=True,
        reply="I'll find a dentist for you next Tuesday afternoon.",
        service_type="dentist",
        date="2026-02-10",
        time_preference="afternoon",
        urgency="specific_date",
    )
    booking = _make_booking()
    intent = chat_response.to_booking_intent()

    with (
        patch(
            "app.routers.chat.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.chat.classify_and_parse",
            return_value=chat_response,
        ),
        patch(
            "app.routers.chat.create_booking",
            return_value=(booking, intent),
        ) as mock_create,
    ):
        response = await client.post(
            "/api/chat",
            json={"message": "I need a dentist next Tuesday afternoon"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["is_booking_request"] is True
    assert data["reply"] == "I'll find a dentist for you next Tuesday afternoon."
    assert data["booking_id"] == str(booking.id)
    assert data["intent"]["service_type"] == "dentist"
    mock_create.assert_awaited_once()


async def test_chat_returns_422_on_classify_error(client):
    with (
        patch(
            "app.routers.chat.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.chat.classify_and_parse",
            side_effect=ValueError("OpenAI API error: connection failed"),
        ),
    ):
        response = await client.post(
            "/api/chat",
            json={"message": "hello"},
        )

    assert response.status_code == 422
    assert "OpenAI API error" in response.json()["detail"]


async def test_chat_returns_422_on_empty_message(client):
    response = await client.post(
        "/api/chat",
        json={"message": ""},
    )
    assert response.status_code == 422


async def test_chat_response_keys_for_conversation(client):
    chat_response = ChatResponse(
        is_booking_request=False,
        reply="Hi there!",
    )

    with (
        patch(
            "app.routers.chat.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.chat.classify_and_parse",
            return_value=chat_response,
        ),
    ):
        response = await client.post(
            "/api/chat",
            json={"message": "hey"},
        )

    data = response.json()
    assert set(data.keys()) == {
        "is_booking_request",
        "reply",
        "booking_id",
        "status",
        "intent",
    }


async def test_chat_passes_history_to_classify(client):
    chat_response = ChatResponse(
        is_booking_request=True,
        reply="A generalist doctor from tomorrow, got it!",
        service_type="generalist doctor",
        date="2026-02-09",
        urgency="specific_date",
    )
    booking = _make_booking(service_type="generalist doctor")
    intent = chat_response.to_booking_intent()

    with (
        patch(
            "app.routers.chat.get_or_create_default_user",
            return_value=_make_user(),
        ),
        patch(
            "app.routers.chat.classify_and_parse",
            return_value=chat_response,
        ) as mock_classify,
        patch(
            "app.routers.chat.create_booking",
            return_value=(booking, intent),
        ),
    ):
        response = await client.post(
            "/api/chat",
            json={
                "message": "from tomorrow",
                "history": [
                    {"role": "user", "content": "I need a generalist doctor"},
                    {
                        "role": "assistant",
                        "content": "Sure! What date works for you?",
                    },
                ],
            },
        )

    assert response.status_code == 200
    mock_classify.assert_awaited_once_with(
        "from tomorrow",
        history=[
            {"role": "user", "content": "I need a generalist doctor"},
            {"role": "assistant", "content": "Sure! What date works for you?"},
        ],
    )
