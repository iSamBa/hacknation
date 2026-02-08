import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.call_result import CallOutcome
from app.schemas.call_result import (
    CallResultCreate,
    CallResultResponse,
    CallResultUpdate,
)


class TestCallResultCreate:
    def test_valid_minimal(self):
        cr = CallResultCreate(
            booking_id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
            call_outcome=CallOutcome.SLOT_OFFERED,
        )
        assert cr.call_outcome == CallOutcome.SLOT_OFFERED
        assert cr.conversation_id is None
        assert cr.transcript is None

    def test_valid_full(self):
        cr = CallResultCreate(
            booking_id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
            conversation_id="conv_abc123",
            call_outcome=CallOutcome.BOOKED_TENTATIVE,
            available_slot=datetime(2026, 3, 1, 10, 0),
            provider_notes="Patient confirmed for 10am",
            transcript={"turns": []},
            call_duration_seconds=120,
            started_at=datetime(2026, 2, 28, 14, 0),
            ended_at=datetime(2026, 2, 28, 14, 2),
        )
        assert cr.call_duration_seconds == 120
        assert cr.available_slot == datetime(2026, 3, 1, 10, 0)

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            CallResultCreate(booking_id=uuid.uuid4())

    def test_invalid_outcome(self):
        with pytest.raises(ValidationError):
            CallResultCreate(
                booking_id=uuid.uuid4(),
                provider_id=uuid.uuid4(),
                call_outcome="invalid",
            )

    def test_negative_duration(self):
        with pytest.raises(ValidationError):
            CallResultCreate(
                booking_id=uuid.uuid4(),
                provider_id=uuid.uuid4(),
                call_outcome=CallOutcome.CALL_FAILED,
                call_duration_seconds=-1,
            )


class TestCallResultUpdate:
    def test_all_optional(self):
        update = CallResultUpdate()
        assert update.call_outcome is None
        assert update.provider_notes is None

    def test_partial(self):
        update = CallResultUpdate(
            call_outcome=CallOutcome.NO_AVAILABILITY,
            provider_notes="Fully booked this week",
        )
        assert update.call_outcome == CallOutcome.NO_AVAILABILITY
        assert update.provider_notes == "Fully booked this week"


class TestCallResultResponse:
    def test_from_dict(self):
        data = {
            "id": uuid.uuid4(),
            "booking_id": uuid.uuid4(),
            "provider_id": uuid.uuid4(),
            "conversation_id": "conv_123",
            "call_outcome": CallOutcome.VOICEMAIL,
            "available_slot": None,
            "provider_notes": None,
            "transcript": None,
            "call_duration_seconds": 30,
            "started_at": datetime.now(),
            "ended_at": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = CallResultResponse(**data)
        assert response.call_outcome == CallOutcome.VOICEMAIL
        assert response.call_duration_seconds == 30

    def test_from_attributes_config(self):
        assert CallResultResponse.model_config["from_attributes"] is True
