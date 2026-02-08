import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.booking import BookingStatus
from app.schemas.booking import (
    BookingCreate,
    BookingProviderCreate,
    BookingProviderResponse,
    BookingProviderUpdate,
    BookingResponse,
    BookingUpdate,
)


class TestBookingCreate:
    def test_valid_minimal(self):
        booking = BookingCreate(
            user_id=uuid.uuid4(),
            service_type="dentist",
            raw_message="I need a dentist appointment",
        )
        assert booking.service_type == "dentist"
        assert booking.status == BookingStatus.SEARCHING
        assert booking.preferred_date is None
        assert booking.constraints is None

    def test_valid_full(self):
        booking = BookingCreate(
            user_id=uuid.uuid4(),
            status=BookingStatus.SHORTLISTING,
            service_type="dentist",
            preferred_date="2026-03-01",
            preferred_time="morning",
            location_override="456 Oak Ave",
            constraints={"max_price": 100},
            raw_message="Find me a dentist near Oak Ave",
        )
        assert booking.status == BookingStatus.SHORTLISTING
        assert booking.constraints == {"max_price": 100}

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            BookingCreate(user_id=uuid.uuid4())

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            BookingCreate(
                user_id=uuid.uuid4(),
                status="invalid_status",
                service_type="dentist",
                raw_message="test",
            )


class TestBookingUpdate:
    def test_all_optional(self):
        update = BookingUpdate()
        assert update.status is None
        assert update.service_type is None

    def test_status_update(self):
        update = BookingUpdate(status=BookingStatus.CONFIRMED)
        assert update.status == BookingStatus.CONFIRMED


class TestBookingResponse:
    def test_from_dict(self):
        data = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "status": BookingStatus.SEARCHING,
            "service_type": "dentist",
            "preferred_date": None,
            "preferred_time": None,
            "location_override": None,
            "constraints": None,
            "raw_message": "test",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = BookingResponse(**data)
        assert response.status == BookingStatus.SEARCHING

    def test_from_attributes_config(self):
        assert BookingResponse.model_config["from_attributes"] is True


class TestBookingProviderCreate:
    def test_valid(self):
        bp = BookingProviderCreate(
            booking_id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
            pre_score=0.85,
        )
        assert bp.pre_score == 0.85
        assert bp.was_called is False
        assert bp.rank is None

    def test_negative_pre_score(self):
        with pytest.raises(ValidationError):
            BookingProviderCreate(
                booking_id=uuid.uuid4(),
                provider_id=uuid.uuid4(),
                pre_score=-1.0,
            )

    def test_rank_must_be_positive(self):
        with pytest.raises(ValidationError):
            BookingProviderCreate(
                booking_id=uuid.uuid4(),
                provider_id=uuid.uuid4(),
                pre_score=0.5,
                rank=0,
            )


class TestBookingProviderUpdate:
    def test_all_optional(self):
        update = BookingProviderUpdate()
        assert update.pre_score is None
        assert update.was_called is None

    def test_partial(self):
        update = BookingProviderUpdate(was_called=True, rank=1)
        assert update.was_called is True
        assert update.rank == 1


class TestBookingProviderResponse:
    def test_from_dict(self):
        data = {
            "id": uuid.uuid4(),
            "booking_id": uuid.uuid4(),
            "provider_id": uuid.uuid4(),
            "pre_score": 0.85,
            "travel_minutes": 12.5,
            "was_called": True,
            "rank": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = BookingProviderResponse(**data)
        assert response.pre_score == 0.85
        assert response.rank == 1

    def test_from_attributes_config(self):
        assert BookingProviderResponse.model_config["from_attributes"] is True
