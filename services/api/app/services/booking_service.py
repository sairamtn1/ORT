from datetime import datetime
from decimal import Decimal
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Booking, BookingStatus, ParkingSlot, SlotStatus, User, UserRole
from ..schemas import BookingCreate


async def create_booking(db: AsyncSession, current_user: User, payload: BookingCreate) -> Booking:
    if current_user.role not in (UserRole.customer, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can create bookings")
    if current_user.role != UserRole.admin and payload.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bookings can only be created for yourself")
    slot = await db.scalar(
        select(ParkingSlot)
        .where(ParkingSlot.id == payload.parking_slot_id)
        .with_for_update()
    )
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking slot not found")
    if slot.status != SlotStatus.available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Parking slot is not available")
    conflict = await db.scalar(
        select(Booking.id).where(
            Booking.parking_slot_id == payload.parking_slot_id,
            Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
            and_(Booking.starts_at < payload.ends_at, Booking.ends_at > payload.starts_at),
        )
    )
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Parking slot is already booked")
    booking = Booking(**payload.model_dump())
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking