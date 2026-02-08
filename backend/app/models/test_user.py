from sqlalchemy import ARRAY, Float, String, inspect

from app.models.user import UserProfile


def test_user_profile_tablename():
    assert UserProfile.__tablename__ == "user_profiles"


def test_user_profile_has_all_fields():
    mapper = inspect(UserProfile)
    expected_fields = [
        "id",
        "created_at",
        "updated_at",
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
        "preferred_providers",
        "blocked_providers",
        "language_preference",
        "google_calendar_id",
    ]
    for field in expected_fields:
        assert field in mapper.columns, f"Missing field: {field}"


def test_user_profile_string_columns():
    mapper = inspect(UserProfile)
    string_fields = {
        "name": 255,
        "phone": 50,
        "email": 255,
        "address": 500,
        "language_preference": 50,
        "google_calendar_id": 255,
    }
    for field, length in string_fields.items():
        col = mapper.columns[field]
        assert isinstance(col.type, String)
        assert col.type.length == length, f"{field} should have length {length}"


def test_user_profile_float_columns():
    mapper = inspect(UserProfile)
    float_fields = ["latitude", "longitude", "max_distance_km", "min_rating"]
    for field in float_fields:
        col = mapper.columns[field]
        assert isinstance(col.type, Float)


def test_user_profile_array_columns():
    mapper = inspect(UserProfile)
    array_fields = [
        "preferred_times",
        "preferred_days",
        "avoid_times",
        "preferred_providers",
        "blocked_providers",
    ]
    for field in array_fields:
        col = mapper.columns[field]
        assert isinstance(col.type, ARRAY)


def test_user_profile_nullable_fields():
    mapper = inspect(UserProfile)
    nullable_fields = [
        "phone",
        "email",
        "avoid_times",
        "google_calendar_id",
    ]
    for field in nullable_fields:
        col = mapper.columns[field]
        assert col.nullable is True, f"{field} should be nullable"


def test_user_profile_required_fields():
    mapper = inspect(UserProfile)
    required_fields = ["name", "address", "latitude", "longitude"]
    for field in required_fields:
        col = mapper.columns[field]
        assert col.nullable is False, f"{field} should be required"


def test_user_profile_defaults():
    mapper = inspect(UserProfile)
    assert mapper.columns["max_distance_km"].default.arg == 10.0
    assert mapper.columns["min_rating"].default.arg == 4.0
    assert mapper.columns["language_preference"].default.arg == "english"


def test_user_profile_server_defaults():
    mapper = inspect(UserProfile)
    fields_with_server_defaults = [
        "max_distance_km",
        "min_rating",
        "language_preference",
        "preferred_times",
        "preferred_days",
        "preferred_providers",
        "blocked_providers",
    ]
    for field in fields_with_server_defaults:
        col = mapper.columns[field]
        assert col.server_default is not None, f"{field} should have a server_default"


def test_user_profile_array_defaults():
    mapper = inspect(UserProfile)
    array_with_defaults = [
        "preferred_times",
        "preferred_days",
        "preferred_providers",
        "blocked_providers",
    ]
    for field in array_with_defaults:
        col = mapper.columns[field]
        assert col.default is not None, f"{field} should have a default"
