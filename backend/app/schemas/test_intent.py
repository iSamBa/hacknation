import pytest
from pydantic import ValidationError

from app.schemas.intent import BookingIntent


class TestBookingIntentValid:
    def test_minimal(self):
        intent = BookingIntent(service_type="dentist")
        assert intent.service_type == "dentist"
        assert intent.date is None
        assert intent.time_preference is None
        assert intent.location_override is None
        assert intent.constraints == []
        assert intent.urgency == "flexible"

    def test_full_fields(self):
        intent = BookingIntent(
            service_type="dentist",
            date="2026-02-10",
            time_preference="afternoon",
            location_override="downtown",
            constraints=["accepts insurance", "wheelchair accessible"],
            urgency="specific_date",
        )
        assert intent.service_type == "dentist"
        assert intent.date == "2026-02-10"
        assert intent.time_preference == "afternoon"
        assert intent.location_override == "downtown"
        assert len(intent.constraints) == 2
        assert intent.urgency == "specific_date"

    def test_asap_urgency(self):
        intent = BookingIntent(service_type="plumber", urgency="asap")
        assert intent.urgency == "asap"

    def test_empty_constraints(self):
        intent = BookingIntent(service_type="restaurant", constraints=[])
        assert intent.constraints == []


class TestBookingIntentValidation:
    def test_missing_service_type(self):
        with pytest.raises(ValidationError):
            BookingIntent()

    def test_empty_service_type(self):
        with pytest.raises(ValidationError):
            BookingIntent(service_type="")

    def test_time_preference_normalized(self):
        intent = BookingIntent(service_type="dentist", time_preference="MORNING")
        assert intent.time_preference == "morning"

    def test_time_preference_afternoon(self):
        intent = BookingIntent(service_type="dentist", time_preference="Afternoon")
        assert intent.time_preference == "afternoon"

    def test_time_preference_evening(self):
        intent = BookingIntent(service_type="dentist", time_preference="EVENING")
        assert intent.time_preference == "evening"

    def test_time_preference_specific_time_passthrough(self):
        intent = BookingIntent(service_type="dentist", time_preference="14:00")
        assert intent.time_preference == "14:00"

    def test_urgency_normalized(self):
        intent = BookingIntent(service_type="dentist", urgency="ASAP")
        assert intent.urgency == "asap"

    def test_invalid_urgency_defaults_to_flexible(self):
        intent = BookingIntent(service_type="dentist", urgency="unknown_value")
        assert intent.urgency == "flexible"

    def test_none_time_preference_allowed(self):
        intent = BookingIntent(service_type="dentist", time_preference=None)
        assert intent.time_preference is None
