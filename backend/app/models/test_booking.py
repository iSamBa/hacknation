from sqlalchemy import Float, Integer, inspect

from app.models.booking import Booking, BookingProvider, BookingStatus


class TestBookingStatus:
    def test_all_pipeline_states_exist(self):
        expected = [
            "searching",
            "shortlisting",
            "calling",
            "collecting",
            "ranking",
            "options_ready",
            "confirmed",
            "cancelled",
            "call_failed",
        ]
        actual = [s.value for s in BookingStatus]
        assert actual == expected

    def test_enum_count(self):
        assert len(BookingStatus) == 9

    def test_string_enum(self):
        assert BookingStatus.SEARCHING == "searching"
        assert isinstance(BookingStatus.SEARCHING, str)


class TestBookingModel:
    def test_booking_tablename(self):
        assert Booking.__tablename__ == "bookings"

    def test_booking_has_all_fields(self):
        mapper = inspect(Booking)
        expected = [
            "id",
            "created_at",
            "updated_at",
            "user_id",
            "status",
            "service_type",
            "preferred_date",
            "preferred_time",
            "location_override",
            "constraints",
            "raw_message",
        ]
        for field in expected:
            assert field in mapper.columns, f"Missing field: {field}"

    def test_booking_user_id_is_foreign_key(self):
        mapper = inspect(Booking)
        col = mapper.columns["user_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "user_profiles.id" in fk_targets

    def test_booking_user_id_is_indexed(self):
        mapper = inspect(Booking)
        assert mapper.columns["user_id"].index is True

    def test_booking_status_default(self):
        mapper = inspect(Booking)
        assert mapper.columns["status"].default.arg is BookingStatus.SEARCHING

    def test_booking_status_server_default(self):
        mapper = inspect(Booking)
        assert mapper.columns["status"].server_default is not None

    def test_booking_user_id_cascade_delete(self):
        mapper = inspect(Booking)
        fks = list(mapper.columns["user_id"].foreign_keys)
        assert fks[0].ondelete == "CASCADE"

    def test_booking_nullable_fields(self):
        mapper = inspect(Booking)
        nullable = [
            "preferred_date",
            "preferred_time",
            "location_override",
            "constraints",
        ]
        for field in nullable:
            assert mapper.columns[field].nullable is True, f"{field} should be nullable"

    def test_booking_required_fields(self):
        mapper = inspect(Booking)
        required = ["user_id", "service_type", "raw_message"]
        for field in required:
            assert mapper.columns[field].nullable is False, (
                f"{field} should be required"
            )


class TestBookingProviderModel:
    def test_booking_provider_tablename(self):
        assert BookingProvider.__tablename__ == "booking_providers"

    def test_booking_provider_has_all_fields(self):
        mapper = inspect(BookingProvider)
        expected = [
            "id",
            "created_at",
            "updated_at",
            "booking_id",
            "provider_id",
            "pre_score",
            "travel_minutes",
            "was_called",
            "rank",
        ]
        for field in expected:
            assert field in mapper.columns, f"Missing field: {field}"

    def test_booking_provider_foreign_keys(self):
        mapper = inspect(BookingProvider)
        booking_fks = [
            fk.target_fullname for fk in mapper.columns["booking_id"].foreign_keys
        ]
        provider_fks = [
            fk.target_fullname for fk in mapper.columns["provider_id"].foreign_keys
        ]
        assert "bookings.id" in booking_fks
        assert "providers.id" in provider_fks

    def test_booking_provider_indexes(self):
        mapper = inspect(BookingProvider)
        assert mapper.columns["booking_id"].index is True
        assert mapper.columns["provider_id"].index is True

    def test_booking_provider_pre_score_is_float(self):
        mapper = inspect(BookingProvider)
        assert isinstance(mapper.columns["pre_score"].type, Float)

    def test_booking_provider_was_called_default(self):
        mapper = inspect(BookingProvider)
        assert mapper.columns["was_called"].default.arg is False

    def test_booking_provider_was_called_server_default(self):
        mapper = inspect(BookingProvider)
        assert mapper.columns["was_called"].server_default is not None

    def test_booking_provider_cascade_deletes(self):
        mapper = inspect(BookingProvider)
        booking_fks = list(mapper.columns["booking_id"].foreign_keys)
        provider_fks = list(mapper.columns["provider_id"].foreign_keys)
        assert booking_fks[0].ondelete == "CASCADE"
        assert provider_fks[0].ondelete == "CASCADE"

    def test_booking_provider_unique_constraint(self):
        constraints = BookingProvider.__table__.constraints
        unique_names = [c.name for c in constraints if hasattr(c, "name") and c.name]
        assert "uq_booking_provider" in unique_names

    def test_booking_provider_nullable_fields(self):
        mapper = inspect(BookingProvider)
        assert mapper.columns["travel_minutes"].nullable is True
        assert mapper.columns["rank"].nullable is True

    def test_booking_provider_rank_is_integer(self):
        mapper = inspect(BookingProvider)
        assert isinstance(mapper.columns["rank"].type, Integer)
