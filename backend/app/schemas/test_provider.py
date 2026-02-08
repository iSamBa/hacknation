import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.provider import ProviderCreate, ProviderResponse, ProviderUpdate


class TestProviderCreate:
    def test_valid(self):
        provider = ProviderCreate(
            place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
            name="Test Provider",
            address="123 Main St",
            latitude=37.7749,
            longitude=-122.4194,
            rating=4.5,
        )
        assert provider.place_id == "ChIJN1t_tDeuEmsRUsoyG83frY4"
        assert provider.review_count == 0
        assert provider.is_open is None

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            ProviderCreate(place_id="abc", name="Test")

    def test_invalid_rating(self):
        with pytest.raises(ValidationError):
            ProviderCreate(
                place_id="abc",
                name="Test",
                address="addr",
                latitude=0,
                longitude=0,
                rating=6.0,
            )

    def test_invalid_latitude(self):
        with pytest.raises(ValidationError):
            ProviderCreate(
                place_id="abc",
                name="Test",
                address="addr",
                latitude=91,
                longitude=0,
                rating=4.0,
            )

    def test_negative_review_count(self):
        with pytest.raises(ValidationError):
            ProviderCreate(
                place_id="abc",
                name="Test",
                address="addr",
                latitude=0,
                longitude=0,
                rating=4.0,
                review_count=-1,
            )


class TestProviderUpdate:
    def test_all_optional(self):
        update = ProviderUpdate()
        assert update.name is None
        assert update.rating is None

    def test_partial(self):
        update = ProviderUpdate(rating=4.8, is_open=True)
        assert update.rating == 4.8
        assert update.is_open is True


class TestProviderResponse:
    def test_from_dict(self):
        data = {
            "id": uuid.uuid4(),
            "place_id": "abc123",
            "name": "Test",
            "address": "addr",
            "latitude": 0.0,
            "longitude": 0.0,
            "phone": None,
            "rating": 4.5,
            "review_count": 10,
            "is_open": True,
            "cached_at": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = ProviderResponse(**data)
        assert response.place_id == "abc123"
        assert response.review_count == 10

    def test_from_attributes_config(self):
        assert ProviderResponse.model_config["from_attributes"] is True
