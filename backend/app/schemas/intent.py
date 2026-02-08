from pydantic import BaseModel, Field, field_validator


class BookingIntent(BaseModel):
    service_type: str = Field(..., min_length=1, max_length=255)
    date: str | None = Field(
        None,
        max_length=50,
        description="ISO date or relative expression resolved to ISO date",
    )
    time_preference: str | None = Field(
        None,
        max_length=50,
        description="morning, afternoon, evening, or specific time",
    )
    location_override: str | None = Field(
        None,
        max_length=500,
        description="Location if user specifies a different area",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Specific requirements like 'accepts insurance'",
    )
    urgency: str = Field(
        default="flexible",
        description="asap, flexible, or specific_date",
    )

    @field_validator("time_preference")
    @classmethod
    def validate_time_preference(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"morning", "afternoon", "evening"}
        if v.lower() in allowed:
            return v.lower()
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        allowed = {"asap", "flexible", "specific_date"}
        if v.lower() not in allowed:
            return "flexible"
        return v.lower()


class ChatResponse(BaseModel):
    """LLM structured output for chat classification and intent parsing."""

    is_booking_request: bool = Field(
        description="True if the user is requesting a booking or appointment",
    )
    reply: str = Field(
        description="Friendly reply to the user",
    )
    service_type: str | None = Field(
        None,
        description="Type of service if booking request (e.g. dentist, plumber)",
    )
    date: str | None = Field(
        None,
        description="ISO date (YYYY-MM-DD) if mentioned",
    )
    time_preference: str | None = Field(
        None,
        description="morning, afternoon, evening, or a specific time",
    )
    location_override: str | None = Field(
        None,
        description="Location if user specifies one different from default",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Specific requirements mentioned",
    )
    urgency: str = Field(
        default="flexible",
        description="asap, flexible, or specific_date",
    )

    def to_booking_intent(self) -> BookingIntent:
        """Convert to BookingIntent. Only call when is_booking_request is True."""
        return BookingIntent(
            service_type=self.service_type or "",
            date=self.date,
            time_preference=self.time_preference,
            location_override=self.location_override,
            constraints=self.constraints,
            urgency=self.urgency,
        )
