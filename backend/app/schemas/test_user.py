import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.user import UserProfileCreate, UserProfileResponse, UserProfileUpdate


class TestUserProfileCreate:
    def test_valid_minimal(self):
        profile = UserProfileCreate(
            name="John Doe",
            address="123 Main St",
            latitude=37.7749,
            longitude=-122.4194,
        )
        assert profile.name == "John Doe"
        assert profile.address == "123 Main St"
        assert profile.latitude == 37.7749
        assert profile.longitude == -122.4194

    def test_defaults_applied(self):
        profile = UserProfileCreate(
            name="John Doe",
            address="123 Main St",
            latitude=37.7749,
            longitude=-122.4194,
        )
        assert profile.max_distance_km == 10.0
        assert profile.min_rating == 4.0
        assert profile.language_preference == "english"
        assert profile.preferred_times == []
        assert profile.preferred_days == []
        assert profile.preferred_providers == []
        assert profile.blocked_providers == []
        assert profile.phone is None
        assert profile.email is None
        assert profile.avoid_times is None
        assert profile.google_calendar_id is None

    def test_valid_full(self):
        profile = UserProfileCreate(
            name="John Doe",
            phone="+1234567890",
            email="john@example.com",
            address="123 Main St",
            latitude=37.7749,
            longitude=-122.4194,
            preferred_times=["morning", "afternoon"],
            preferred_days=["monday", "wednesday"],
            avoid_times=["evening"],
            max_distance_km=15.0,
            min_rating=4.5,
            preferred_providers=["place_abc"],
            blocked_providers=["place_xyz"],
            language_preference="french",
            google_calendar_id="cal_123",
        )
        assert profile.phone == "+1234567890"
        assert profile.preferred_times == ["morning", "afternoon"]
        assert profile.language_preference == "french"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(
                name="John Doe",
                # missing address, latitude, longitude
            )

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(
                name="x" * 256,
                address="123 Main St",
                latitude=37.7749,
                longitude=-122.4194,
            )

    def test_invalid_latitude_too_high(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(name="John", address="123 St", latitude=91, longitude=0)

    def test_invalid_latitude_too_low(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(name="John", address="123 St", latitude=-91, longitude=0)

    def test_invalid_longitude_too_high(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(name="John", address="123 St", latitude=0, longitude=181)

    def test_invalid_longitude_too_low(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(name="John", address="123 St", latitude=0, longitude=-181)

    def test_invalid_min_rating_too_high(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(
                name="John",
                address="123 St",
                latitude=0,
                longitude=0,
                min_rating=5.1,
            )

    def test_invalid_min_rating_negative(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(
                name="John",
                address="123 St",
                latitude=0,
                longitude=0,
                min_rating=-1.0,
            )

    def test_invalid_max_distance_zero(self):
        with pytest.raises(ValidationError):
            UserProfileCreate(
                name="John",
                address="123 St",
                latitude=0,
                longitude=0,
                max_distance_km=0,
            )


class TestUserProfileUpdate:
    def test_all_fields_optional(self):
        profile = UserProfileUpdate()
        assert profile.name is None
        assert profile.address is None
        assert profile.latitude is None

    def test_partial_update(self):
        profile = UserProfileUpdate(name="New Name", min_rating=4.8)
        assert profile.name == "New Name"
        assert profile.min_rating == 4.8
        assert profile.address is None


class TestUserProfileResponse:
    def test_from_dict(self):
        data = {
            "id": uuid.uuid4(),
            "name": "John Doe",
            "phone": None,
            "email": "john@example.com",
            "address": "123 Main St",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "preferred_times": ["morning"],
            "preferred_days": ["monday"],
            "avoid_times": None,
            "max_distance_km": 10.0,
            "min_rating": 4.0,
            "preferred_providers": [],
            "blocked_providers": [],
            "language_preference": "english",
            "google_calendar_id": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = UserProfileResponse(**data)
        assert response.name == "John Doe"
        assert isinstance(response.id, uuid.UUID)
        assert response.preferred_times == ["morning"]

    def test_from_attributes_config(self):
        assert UserProfileResponse.model_config["from_attributes"] is True
