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
