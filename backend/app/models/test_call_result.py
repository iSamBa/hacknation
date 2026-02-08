from sqlalchemy import Integer, String, inspect
from sqlalchemy.dialects.postgresql import JSONB

from app.models.call_result import CallOutcome, CallResult


class TestCallOutcome:
    def test_all_outcomes_exist(self):
        expected = [
            "slot_offered",
            "booked_tentative",
            "no_availability",
            "voicemail",
            "call_failed",
            "cancelled",
        ]
        actual = [o.value for o in CallOutcome]
        assert actual == expected

    def test_enum_count(self):
        assert len(CallOutcome) == 6

    def test_string_enum(self):
        assert CallOutcome.SLOT_OFFERED == "slot_offered"
        assert isinstance(CallOutcome.SLOT_OFFERED, str)


class TestCallResultModel:
    def test_tablename(self):
        assert CallResult.__tablename__ == "call_results"

    def test_has_all_fields(self):
        mapper = inspect(CallResult)
        expected = [
            "id",
            "created_at",
            "updated_at",
            "booking_id",
            "provider_id",
            "conversation_id",
            "call_outcome",
            "available_slot",
            "provider_notes",
            "transcript",
            "call_duration_seconds",
            "started_at",
            "ended_at",
        ]
        for field in expected:
            assert field in mapper.columns, f"Missing field: {field}"

    def test_booking_id_foreign_key(self):
        mapper = inspect(CallResult)
        fks = [fk.target_fullname for fk in mapper.columns["booking_id"].foreign_keys]
        assert "bookings.id" in fks

    def test_provider_id_foreign_key(self):
        mapper = inspect(CallResult)
        fks = [fk.target_fullname for fk in mapper.columns["provider_id"].foreign_keys]
        assert "providers.id" in fks

    def test_foreign_key_indexes(self):
        mapper = inspect(CallResult)
        assert mapper.columns["booking_id"].index is True
        assert mapper.columns["provider_id"].index is True

    def test_cascade_deletes(self):
        mapper = inspect(CallResult)
        booking_fks = list(mapper.columns["booking_id"].foreign_keys)
        provider_fks = list(mapper.columns["provider_id"].foreign_keys)
        assert booking_fks[0].ondelete == "CASCADE"
        assert provider_fks[0].ondelete == "CASCADE"

    def test_conversation_id_column(self):
        mapper = inspect(CallResult)
        col = mapper.columns["conversation_id"]
        assert isinstance(col.type, String)
        assert col.type.length == 255
        assert col.nullable is True

    def test_transcript_is_jsonb(self):
        mapper = inspect(CallResult)
        assert isinstance(mapper.columns["transcript"].type, JSONB)

    def test_call_duration_is_integer(self):
        mapper = inspect(CallResult)
        assert isinstance(mapper.columns["call_duration_seconds"].type, Integer)

    def test_nullable_fields(self):
        mapper = inspect(CallResult)
        nullable = [
            "conversation_id",
            "available_slot",
            "provider_notes",
            "transcript",
            "call_duration_seconds",
            "started_at",
            "ended_at",
        ]
        for field in nullable:
            assert mapper.columns[field].nullable is True, f"{field} should be nullable"

    def test_required_fields(self):
        mapper = inspect(CallResult)
        required = ["booking_id", "provider_id", "call_outcome"]
        for field in required:
            assert mapper.columns[field].nullable is False, (
                f"{field} should be required"
            )
