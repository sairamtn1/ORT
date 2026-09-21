import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Booking, Owner, ParkingLot, ParkingSlot, Payment, Review, User, UserRole


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin


def ensure_admin_or_self(user: User, user_id: uuid.UUID) -> None:
    if not is_admin(user) and user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resource access denied")


async def get_owner_for_user(db: AsyncSession, user: User) -> Owner | None:
    return await db.scalar(select(Owner).where(Owner.user_id == user.id))


async def ensure_owner_or_admin(db: AsyncSession, user: User, owner_id: uuid.UUID) -> None:
    if is_admin(user):
        return
    owner = await get_owner_for_user(db, user)
    if not owner or owner.id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")


async def ensure_lot_access(db: AsyncSession, user: User, lot_id: uuid.UUID) -> ParkingLot:
    lot = await db.get(ParkingLot, lot_id)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking lot not found")
    if is_admin(user):
        return lot
    owner = await get_owner_for_user(db, user)
    if not owner or owner.id != lot.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parking lot access denied")
    return lot


async def ensure_slot_access(db: AsyncSession, user: User, slot_id: uuid.UUID) -> ParkingSlot:
    slot = await db.get(ParkingSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking slot not found")
    await ensure_lot_access(db, user, slot.parking_lot_id)
    return slot


async def ensure_booking_access(db: AsyncSession, user: User, booking_id: uuid.UUID) -> Booking:
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if is_admin(user) or booking.customer_id == user.id:
        return booking
    slot = await db.get(ParkingSlot, booking.parking_slot_id)
    if slot:
        await ensure_lot_access(db, user, slot.parking_lot_id)
        return booking
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Booking access denied")


async def ensure_payment_access(db: AsyncSession, user: User, payment_id: uuid.UUID) -> Payment:
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    await ensure_booking_access(db, user, payment.booking_id)
    return payment


async def ensure_review_access(db: AsyncSession, user: User, review_id: uuid.UUID) -> Review:
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if is_admin(user) or review.customer_id == user.id:
        return review
    booking = await db.get(Booking, review.booking_id)
    if booking:
        await ensure_booking_access(db, user, booking.id)
        return review
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review access denied")