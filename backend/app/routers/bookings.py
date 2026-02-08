import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.booking import (
    BookingRequest,
    BookingRequestResponse,
    BookingResponse,
    ShortlistItemResponse,
)
from app.services.booking_service import (
    create_booking,
    get_booking,
    get_shortlist,
    list_bookings,
)
from app.services.pipeline import start_pipeline
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


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking_endpoint(booking_id: uuid.UUID, db: DbSession):
    booking = await get_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("", response_model=list[BookingResponse])
async def list_bookings_endpoint(db: DbSession):
    user = await get_or_create_default_user(db)
    return await list_bookings(db, user.id)
