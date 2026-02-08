from datetime import date

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from app.config import settings
from app.schemas.intent import BookingIntent, ChatResponse

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a warm, professional concierge who helps people book "
    "appointments and services. Never refer to yourself as a chatbot, "
    "bot, or AI. Speak naturally, like a helpful human assistant.\n"
    "\n"
    "You will receive the full conversation history. Use it to "
    "understand context: if the user's latest message is a follow-up "
    "answer (e.g. a date, time, or detail that completes an earlier "
    "booking request), combine it with the prior context to form a "
    "complete booking.\n"
    "\n"
    "Today's date is {today}.\n"
    "\n"
    "If the message (considering conversation history) is NOT a "
    "booking request:\n"
    "- Set is_booking_request to false\n"
    "- Set reply to a friendly, helpful response.\n"
    "- Leave all booking fields as null/empty.\n"
    "\n"
    "If the message (considering conversation history) IS or "
    "completes a booking request:\n"
    "- Set is_booking_request to true\n"
    "- Set reply to a brief confirmation of what you understood\n"
    "- service_type: The type of service or provider needed "
    "(e.g. dentist, plumber, restaurant)\n"
    "- date: ISO date (YYYY-MM-DD) if mentioned. Resolve relative "
    "references like next Tuesday, tomorrow, this Friday\n"
    "- time_preference: One of morning (8-12), afternoon (12-17), "
    "evening (17-21), or a specific time\n"
    "- location_override: Only if the user specifies a location "
    "different from their default\n"
    "- constraints: Specific requirements (e.g. accepts insurance, "
    "wheelchair accessible). Empty array if none.\n"
    "- urgency: asap if urgent, specific_date if a date is given, "
    "flexible if no time pressure"
)

BOOKING_ONLY_SYSTEM_PROMPT = (
    "You are an intent parser for a booking assistant.\n"
    "Extract structured booking information from the user's message.\n"
    "Today's date is {today}.\n"
    "\n"
    "Return JSON with these fields:\n"
    "- service_type (string, required): The type of service or "
    "provider needed (e.g. dentist, plumber, restaurant)\n"
    "- date (string or null): ISO date (YYYY-MM-DD) if mentioned. "
    "Resolve relative references like next Tuesday, tomorrow, "
    "this Friday relative to today's date.\n"
    "- time_preference (string or null): One of morning (8-12), "
    "afternoon (12-17), evening (17-21), or a specific time\n"
    "- location_override (string or null): Only if the user "
    "specifies a location different from their default\n"
    "- constraints (array of strings): List of specific "
    "requirements mentioned (e.g. accepts insurance, "
    "wheelchair accessible). Empty array if none.\n"
    "- urgency (string): asap if the user expresses urgency, "
    "specific_date if a date is given, flexible if no time "
    "pressure indicated"
)


async def classify_and_parse(
    message: str,
    history: list[dict] | None = None,
) -> ChatResponse:
    """Classify a message and extract booking intent if applicable."""
    if not message or not message.strip():
        raise ValueError("Message cannot be empty")

    today = date.today().isoformat()

    messages: list[dict] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(today=today),
        },
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        completion = await client.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=ChatResponse,
        )
    except (APIConnectionError, RateLimitError, APIError) as e:
        raise ValueError(
            f"OpenAI API error: {e}"
        ) from e

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        refusal = completion.choices[0].message.refusal
        raise ValueError(
            refusal or "Failed to process the message."
        )

    return parsed


async def parse_booking_intent(message: str) -> BookingIntent:
    """Extract structured booking intent from a natural language message."""
    if not message or not message.strip():
        raise ValueError("Message cannot be empty")

    today = date.today().isoformat()

    try:
        completion = await client.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": BOOKING_ONLY_SYSTEM_PROMPT.format(today=today),
                },
                {"role": "user", "content": message},
            ],
            response_format=BookingIntent,
        )
    except (APIConnectionError, RateLimitError, APIError) as e:
        raise ValueError(
            f"OpenAI API error: {e}"
        ) from e

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        refusal = completion.choices[0].message.refusal
        raise ValueError(
            refusal or "Failed to parse booking intent from the message."
        )

    return parsed
