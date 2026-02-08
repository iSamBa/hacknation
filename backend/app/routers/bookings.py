import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.websocket_manager import ws_manager
from app.models.booking import Booking, BookingStatus
from app.schemas.booking import (
    BookingListResponse,
    BookingRequest,
    BookingRequestResponse,
    BookingResponse,
    ConfirmBookingRequest,
    ConfirmBookingResponse,
    RankedResultResponse,
    ShortlistItemResponse,
)
from app.services.booking_service import (
    confirm_booking,
    create_booking,
    get_booking,
    get_shortlist,
    list_bookings,
)
from app.services.pipeline import start_pipeline
from app.services.ranking import rank_results
from app.services.user_service import get_or_create_default_user

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=BookingRequestResponse, status_code=201)
async def create_booking_endpoint(body: BookingRequest, db: DbSession):
    user = await get_or_create_default_user(db)
    try:
        booking, intent = await create_booking(db, user.id, body.message)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    start_pipeline(booking.id)
    return BookingRequestResponse(
        booking_id=booking.id,
        status=booking.status,
        intent=intent,
    )


@router.get(
    "/{booking_id}/shortlist",
    response_model=list[ShortlistItemResponse],
)
async def get_shortlist_endpoint(booking_id: uuid.UUID, db: DbSession):
    booking = await get_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return await get_shortlist(db, booking_id)


@router.get(
    "/{booking_id}/results",
    response_model=list[RankedResultResponse],
)
async def get_results_endpoint(booking_id: uuid.UUID, db: DbSession):
    booking = await get_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    try:
        results = await rank_results(db, booking_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return [
        RankedResultResponse(
            rank=r.rank,
            provider_name=r.provider_name,
            place_id=r.place_id,
            slot=r.slot,
            travel_minutes=r.travel_minutes,
            rating=r.rating,
            review_count=r.review_count,
            score=r.score,
            notes=r.notes,
            provider_id=r.provider_id,
            call_outcome=r.call_outcome,
        )
        for r in results
    ]


@router.post(
    "/{booking_id}/confirm",
    response_model=ConfirmBookingResponse,
)
async def confirm_booking_endpoint(
    booking_id: uuid.UUID,
    body: ConfirmBookingRequest,
    db: DbSession,
):
    booking = await get_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    try:
        return await confirm_booking(db, booking_id, body.provider_id, body.slot)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking_endpoint(booking_id: uuid.UUID, db: DbSession):
    booking = await get_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("", response_model=list[BookingListResponse])
async def list_bookings_endpoint(db: DbSession):
    user = await get_or_create_default_user(db)
    bookings = await list_bookings(db, user.id)
    return [
        BookingListResponse(
            id=b.id,
            user_id=b.user_id,
            status=b.status,
            service_type=b.service_type,
            preferred_date=b.preferred_date,
            preferred_time=b.preferred_time,
            location_override=b.location_override,
            constraints=b.constraints,
            raw_message=b.raw_message,
            created_at=b.created_at,
            updated_at=b.updated_at,
            provider_count=len(b.booking_providers),
            called_count=sum(1 for bp in b.booking_providers if bp.was_called),
        )
        for b in bookings
    ]


@router.post("/{booking_id}/complete-calling", status_code=200)
async def complete_calling_endpoint(booking_id: uuid.UUID, db: DbSession):
    """Complete the calling phase and transition to options_ready.

    DEMO MODE: This endpoint is called after the ElevenLabs widget conversation ends.
    It transitions the booking from CALLING to OPTIONS_READY status.
    """
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != BookingStatus.CALLING:
        raise HTTPException(
            status_code=400,
            detail=f"Booking is not in CALLING status (current: {booking.status.value})",
        )

    # Transition to OPTIONS_READY
    booking.status = BookingStatus.OPTIONS_READY
    await db.commit()

    # Notify frontend via WebSocket
    await ws_manager.send_to_booking(
        booking_id,
        {
            "type": "status",
            "status": BookingStatus.OPTIONS_READY.value,
            "booking_id": str(booking_id),
        },
    )

    return {"status": "success", "new_status": BookingStatus.OPTIONS_READY.value}


@router.delete("/all", status_code=200)
async def delete_all_bookings_endpoint(db: DbSession):
    """Delete all bookings from the database.

    WARNING: This is for development/testing only. It deletes ALL bookings
    and related records.
    """
    from app.models.call_result import CallResult
    from app.models.booking import BookingProvider

    # Delete in correct order to avoid foreign key constraints
    call_results = await db.execute(select(CallResult))
    for cr in call_results.scalars():
        await db.delete(cr)

    booking_providers = await db.execute(select(BookingProvider))
    for bp in booking_providers.scalars():
        await db.delete(bp)

    bookings = await db.execute(select(Booking))
    count = 0
    for b in bookings.scalars():
        await db.delete(b)
        count += 1

    await db.commit()

    return {"status": "success", "deleted_bookings": count}
