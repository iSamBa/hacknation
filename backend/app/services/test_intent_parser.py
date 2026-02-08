from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIConnectionError, RateLimitError

from app.schemas.intent import BookingIntent, ChatResponse
from app.services.intent_parser import classify_and_parse, parse_booking_intent


def _make_completion(parsed, refusal: str | None = None):
    """Build a mock ParsedChatCompletion."""
    message = MagicMock()
    message.parsed = parsed
    message.refusal = refusal
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    return completion


class TestParseBookingIntent:
    @pytest.mark.asyncio
    async def test_dentist_next_tuesday_afternoon(self):
        expected = BookingIntent(
            service_type="dentist",
            date="2026-02-10",
            time_preference="afternoon",
            location_override=None,
            constraints=[],
            urgency="specific_date",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await parse_booking_intent(
                "I need a dentist next Tuesday afternoon"
            )

        assert result.service_type == "dentist"
        assert result.date == "2026-02-10"
        assert result.time_preference == "afternoon"
        assert result.urgency == "specific_date"
        mock_parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_restaurant_friday_evening(self):
        expected = BookingIntent(
            service_type="restaurant",
            date="2026-02-13",
            time_preference="evening",
            constraints=[],
            urgency="specific_date",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await parse_booking_intent(
                "Book a restaurant for Friday evening"
            )

        assert result.service_type == "restaurant"
        assert result.time_preference == "evening"

    @pytest.mark.asyncio
    async def test_plumber_asap(self):
        expected = BookingIntent(
            service_type="plumber",
            urgency="asap",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await parse_booking_intent("Plumber ASAP")

        assert result.service_type == "plumber"
        assert result.urgency == "asap"
        assert result.date is None

    @pytest.mark.asyncio
    async def test_haircut_flexible(self):
        expected = BookingIntent(
            service_type="hair salon",
            urgency="flexible",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await parse_booking_intent("Haircut sometime this week")

        assert result.service_type == "hair salon"
        assert result.urgency == "flexible"

    @pytest.mark.asyncio
    async def test_location_override(self):
        expected = BookingIntent(
            service_type="coffee shop",
            location_override="near the airport",
            urgency="flexible",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await parse_booking_intent(
                "Find a coffee shop near the airport"
            )

        assert result.location_override == "near the airport"

    @pytest.mark.asyncio
    async def test_multiple_constraints(self):
        expected = BookingIntent(
            service_type="dentist",
            constraints=["accepts insurance", "wheelchair accessible"],
            urgency="flexible",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await parse_booking_intent(
                "Dentist that accepts insurance and is wheelchair accessible"
            )

        assert len(result.constraints) == 2
        assert "accepts insurance" in result.constraints

    @pytest.mark.asyncio
    async def test_refusal_raises_error(self):
        mock_parse = AsyncMock(
            return_value=_make_completion(None, refusal="I cannot process this.")
        )

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            with pytest.raises(ValueError, match="I cannot process this"):
                await parse_booking_intent("some nonsense input")

    @pytest.mark.asyncio
    async def test_none_parsed_no_refusal_raises_error(self):
        mock_parse = AsyncMock(return_value=_make_completion(None))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            with pytest.raises(ValueError, match="Failed to parse"):
                await parse_booking_intent("???")

    @pytest.mark.asyncio
    async def test_model_and_response_format_passed(self):
        expected = BookingIntent(service_type="dentist")
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            await parse_booking_intent("dentist")

        call_kwargs = mock_parse.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["response_format"] is BookingIntent

    @pytest.mark.asyncio
    async def test_system_prompt_contains_today(self):
        expected = BookingIntent(service_type="dentist")
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            await parse_booking_intent("dentist")

        call_kwargs = mock_parse.call_args.kwargs
        system_msg = call_kwargs["messages"][0]["content"]
        assert "Today's date is" in system_msg

    @pytest.mark.asyncio
    async def test_user_message_forwarded(self):
        expected = BookingIntent(service_type="dentist")
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            await parse_booking_intent("I need a dentist please")

        call_kwargs = mock_parse.call_args.kwargs
        user_msg = call_kwargs["messages"][1]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "I need a dentist please"

    @pytest.mark.asyncio
    async def test_empty_message_raises_error(self):
        with pytest.raises(ValueError, match="Message cannot be empty"):
            await parse_booking_intent("")

    @pytest.mark.asyncio
    async def test_whitespace_message_raises_error(self):
        with pytest.raises(ValueError, match="Message cannot be empty"):
            await parse_booking_intent("   ")

    @pytest.mark.asyncio
    async def test_api_connection_error(self):
        mock_parse = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            with pytest.raises(ValueError, match="OpenAI API error"):
                await parse_booking_intent("dentist")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        response = MagicMock()
        response.status_code = 429
        response.headers = {}
        mock_parse = AsyncMock(
            side_effect=RateLimitError(
                message="rate limited",
                response=response,
                body=None,
            )
        )

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            with pytest.raises(ValueError, match="OpenAI API error"):
                await parse_booking_intent("dentist")


class TestClassifyAndParse:
    @pytest.mark.asyncio
    async def test_greeting_returns_non_booking(self):
        expected = ChatResponse(
            is_booking_request=False,
            reply="Hello! How can I help you today?",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await classify_and_parse("hi")

        assert result.is_booking_request is False
        assert result.reply == "Hello! How can I help you today?"
        assert result.service_type is None

    @pytest.mark.asyncio
    async def test_booking_request_returns_intent(self):
        expected = ChatResponse(
            is_booking_request=True,
            reply="I'll find a dentist for you next Tuesday afternoon.",
            service_type="dentist",
            date="2026-02-10",
            time_preference="afternoon",
            urgency="specific_date",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            result = await classify_and_parse(
                "I need a dentist next Tuesday afternoon"
            )

        assert result.is_booking_request is True
        assert result.service_type == "dentist"
        assert result.date == "2026-02-10"

    @pytest.mark.asyncio
    async def test_to_booking_intent_conversion(self):
        chat_response = ChatResponse(
            is_booking_request=True,
            reply="Got it!",
            service_type="plumber",
            date="2026-02-12",
            time_preference="morning",
            location_override="downtown",
            constraints=["emergency"],
            urgency="asap",
        )
        intent = chat_response.to_booking_intent()
        assert isinstance(intent, BookingIntent)
        assert intent.service_type == "plumber"
        assert intent.date == "2026-02-12"
        assert intent.urgency == "asap"

    @pytest.mark.asyncio
    async def test_empty_message_raises_error(self):
        with pytest.raises(ValueError, match="Message cannot be empty"):
            await classify_and_parse("")

    @pytest.mark.asyncio
    async def test_uses_chat_response_format(self):
        expected = ChatResponse(
            is_booking_request=False,
            reply="Hi there!",
        )
        mock_parse = AsyncMock(return_value=_make_completion(expected))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            await classify_and_parse("hello")

        call_kwargs = mock_parse.call_args.kwargs
        assert call_kwargs["response_format"] is ChatResponse

    @pytest.mark.asyncio
    async def test_api_error_raises_value_error(self):
        mock_parse = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            with pytest.raises(ValueError, match="OpenAI API error"):
                await classify_and_parse("hi")

    @pytest.mark.asyncio
    async def test_none_parsed_raises_error(self):
        mock_parse = AsyncMock(return_value=_make_completion(None))

        with patch(
            "app.services.intent_parser.client.chat.completions.parse",
            mock_parse,
        ):
            with pytest.raises(ValueError, match="Failed to process"):
                await classify_and_parse("hi")
