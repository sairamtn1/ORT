import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ...dependencies import get_current_user, require_roles
from ...models import (
    AccountStatus,
    Admin,
    Booking,
    Notification,
    Owner,
    ParkingLot,
    ParkingSlot,
    Payment,
    Review,
    User,
    UserRole,
)
from ...repositories import Repository
from ...schemas import (
    AdminCreate,
    AdminRead,
    AdminUpdate,
    BookingCreate,
    BookingRead,
    BookingUpdate,
    NotificationCreate,
    NotificationRead,
    NotificationUpdate,
    OwnerCreate,
    OwnerRead,
    OwnerUpdate,
    ParkingLotCreate,
    ParkingLotRead,
    ParkingLotUpdate,
    ParkingSlotCreate,
    ParkingSlotRead,
    ParkingSlotUpdate,
    PaymentCreate,
    PaymentRead,
    PaymentUpdate,
    ReviewCreate,
    ReviewRead,
    ReviewUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)
from ...security import hash_password
from ...services.authorization import (
    ensure_booking_access,
    ensure_lot_access,
    ensure_owner_or_admin,
    ensure_payment_access,
    ensure_review_access,
    ensure_slot_access,
    is_admin,
)
from ...services.booking_service import create_booking

router = APIRouter()


def values(payload: Any) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


async def list_entities(model: type, db: AsyncSession, limit: int, offset: int):
    return list(await Repository(model, db).list(limit=limit, offset=offset))


def pagination() -> tuple[int, int]:
    return (
        Query(default=100, ge=1, le=100),
        Query(default=0, ge=0),
    )


@router.get("/users", response_model=list[UserRead], tags=["users"])
async def list_users(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    return await list_entities(User, db, limit, offset)


@router.post("/users", response_model=UserRead, status_code=201, tags=["users"])
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    data = values(payload)
    data["email"] = data["email"].lower()
    data["password_hash"] = hash_password(data.pop("password"))
    return await Repository(User, db).create(data)


@router.get("/users/{user_id}", response_model=UserRead, tags=["users"])
async def get_user(
    user_id: uuid.UUID,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(current) and current.id != user_id:
        raise HTTPException(status_code=403, detail="User access denied")
    entity = await db.get(User, user_id)
    if not entity:
        raise HTTPException(status_code=404, detail="User not found")
    return entity


@router.patch("/users/{user_id}", response_model=UserRead, tags=["users"])
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(current) and current.id != user_id:
        raise HTTPException(status_code=403, detail="User access denied")
    entity = await db.get(User, user_id)
    if not entity:
        raise HTTPException(status_code=404, detail="User not found")
    data = values(payload)
    if not is_admin(current):
        data.pop("role", None)
        data.pop("status", None)
    return await Repository(User, db).update(entity, data)


@router.delete("/users/{user_id}", status_code=204, tags=["users"])
async def delete_user(
    user_id: uuid.UUID,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(current) and current.id != user_id:
        raise HTTPException(status_code=403, detail="User access denied")
    entity = await db.get(User, user_id)
    if not entity:
        raise HTTPException(status_code=404, detail="User not found")
    entity.status = AccountStatus.deleted
    await db.commit()


@router.get("/owners", response_model=list[OwnerRead], tags=["owners"])
async def list_owners(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_entities(Owner, db, limit, offset)


@router.post("/owners", response_model=OwnerRead, status_code=201, tags=["owners"])
async def create_owner(
    payload: OwnerCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(current) and current.id != payload.user_id:
        raise HTTPException(status_code=403, detail="Owners can only create their own profile")
    if await db.scalar(select(Owner).where(Owner.user_id == payload.user_id)):
        raise HTTPException(status_code=409, detail="Owner profile already exists")
    return await Repository(Owner, db).create(values(payload))


@router.get("/owners/{owner_id}", response_model=OwnerRead, tags=["owners"])
async def get_owner(owner_id: uuid.UUID, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Owner, owner_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Owner not found")
    return entity


@router.patch("/owners/{owner_id}", response_model=OwnerRead, tags=["owners"])
async def update_owner(
    owner_id: uuid.UUID,
    payload: OwnerUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entity = await db.get(Owner, owner_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Owner not found")
    await ensure_owner_or_admin(db, current, owner_id)
    return await Repository(Owner, db).update(entity, values(payload))


@router.delete("/owners/{owner_id}", status_code=204, tags=["owners"])
async def delete_owner(owner_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Owner, owner_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Owner not found")
    await ensure_owner_or_admin(db, current, owner_id)
    await Repository(Owner, db).delete(entity)


@router.get("/admins", response_model=list[AdminRead], tags=["admins"])
async def list_admins(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    return await list_entities(Admin, db, limit, offset)


@router.post("/admins", response_model=AdminRead, status_code=201, tags=["admins"])
async def create_admin(payload: AdminCreate, _: User = Depends(require_roles(UserRole.admin)), db: AsyncSession = Depends(get_db)):
    return await Repository(Admin, db).create(values(payload))


@router.get("/admins/{admin_id}", response_model=AdminRead, tags=["admins"])
async def get_admin(admin_id: uuid.UUID, _: User = Depends(require_roles(UserRole.admin)), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Admin, admin_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Admin not found")
    return entity


@router.patch("/admins/{admin_id}", response_model=AdminRead, tags=["admins"])
async def update_admin(admin_id: uuid.UUID, payload: AdminUpdate, _: User = Depends(require_roles(UserRole.admin)), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Admin, admin_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Admin not found")
    return await Repository(Admin, db).update(entity, values(payload))


@router.delete("/admins/{admin_id}", status_code=204, tags=["admins"])
async def delete_admin(admin_id: uuid.UUID, _: User = Depends(require_roles(UserRole.admin)), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Admin, admin_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Admin not found")
    await Repository(Admin, db).delete(entity)


@router.get("/parking-lots", response_model=list[ParkingLotRead], tags=["parking lots"])
async def list_parking_lots(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_entities(ParkingLot, db, limit, offset)


@router.post("/parking-lots", response_model=ParkingLotRead, status_code=201, tags=["parking lots"])
async def create_parking_lot(
    payload: ParkingLotCreate,
    current: User = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    await ensure_owner_or_admin(db, current, payload.owner_id)
    return await Repository(ParkingLot, db).create(values(payload))


@router.get("/parking-lots/{lot_id}", response_model=ParkingLotRead, tags=["parking lots"])
async def get_parking_lot(lot_id: uuid.UUID, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await db.get(ParkingLot, lot_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    return entity


@router.patch("/parking-lots/{lot_id}", response_model=ParkingLotRead, tags=["parking lots"])
async def update_parking_lot(
    lot_id: uuid.UUID,
    payload: ParkingLotUpdate,
    current: User = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    entity = await ensure_lot_access(db, current, lot_id)
    return await Repository(ParkingLot, db).update(entity, values(payload))


@router.delete("/parking-lots/{lot_id}", status_code=204, tags=["parking lots"])
async def delete_parking_lot(
    lot_id: uuid.UUID,
    current: User = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    entity = await ensure_lot_access(db, current, lot_id)
    await Repository(ParkingLot, db).delete(entity)


@router.get("/parking-slots", response_model=list[ParkingSlotRead], tags=["parking slots"])
async def list_parking_slots(
    parking_lot_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ParkingSlot).order_by(ParkingSlot.created_at.desc()).limit(limit).offset(offset)
    if parking_lot_id:
        query = query.where(ParkingSlot.parking_lot_id == parking_lot_id)
    return list((await db.scalars(query)).all())


@router.post("/parking-slots", response_model=ParkingSlotRead, status_code=201, tags=["parking slots"])
async def create_parking_slot(
    payload: ParkingSlotCreate,
    current: User = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    await ensure_lot_access(db, current, payload.parking_lot_id)
    return await Repository(ParkingSlot, db).create(values(payload))


@router.get("/parking-slots/{slot_id}", response_model=ParkingSlotRead, tags=["parking slots"])
async def get_parking_slot(slot_id: uuid.UUID, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await db.get(ParkingSlot, slot_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Parking slot not found")
    return entity


@router.patch("/parking-slots/{slot_id}", response_model=ParkingSlotRead, tags=["parking slots"])
async def update_parking_slot(
    slot_id: uuid.UUID,
    payload: ParkingSlotUpdate,
    current: User = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    entity = await ensure_slot_access(db, current, slot_id)
    return await Repository(ParkingSlot, db).update(entity, values(payload))


@router.delete("/parking-slots/{slot_id}", status_code=204, tags=["parking slots"])
async def delete_parking_slot(
    slot_id: uuid.UUID,
    current: User = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    entity = await ensure_slot_access(db, current, slot_id)
    await Repository(ParkingSlot, db).delete(entity)


@router.get("/bookings", response_model=list[BookingRead], tags=["bookings"])
async def list_bookings(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Booking).order_by(Booking.created_at.desc()).limit(limit).offset(offset)
    if not is_admin(current):
        query = query.where(Booking.customer_id == current.id)
    return list((await db.scalars(query)).all())


@router.post("/bookings", response_model=BookingRead, status_code=201, tags=["bookings"])
async def create_booking_controller(payload: BookingCreate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_booking(db, current, payload)


@router.get("/bookings/{booking_id}", response_model=BookingRead, tags=["bookings"])
async def get_booking(booking_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ensure_booking_access(db, current, booking_id)


@router.patch("/bookings/{booking_id}", response_model=BookingRead, tags=["bookings"])
async def update_booking(
    booking_id: uuid.UUID,
    payload: BookingUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entity = await ensure_booking_access(db, current, booking_id)
    data = values(payload)
    if not is_admin(current) and current.role == UserRole.customer:
        data = {key: value for key, value in data.items() if key == "status"}
    return await Repository(Booking, db).update(entity, data)


@router.delete("/bookings/{booking_id}", status_code=204, tags=["bookings"])
async def delete_booking(booking_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await ensure_booking_access(db, current, booking_id)
    await Repository(Booking, db).delete(entity)


@router.get("/payments", response_model=list[PaymentRead], tags=["payments"])
async def list_payments(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Payment).order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    if not is_admin(current):
        query = query.join(Booking).where(Booking.customer_id == current.id)
    return list((await db.scalars(query)).all())


@router.post("/payments", response_model=PaymentRead, status_code=201, tags=["payments"])
async def create_payment(payload: PaymentCreate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_booking_access(db, current, payload.booking_id)
    return await Repository(Payment, db).create(values(payload))


@router.get("/payments/{payment_id}", response_model=PaymentRead, tags=["payments"])
async def get_payment(payment_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ensure_payment_access(db, current, payment_id)


@router.patch("/payments/{payment_id}", response_model=PaymentRead, tags=["payments"])
async def update_payment(
    payment_id: uuid.UUID,
    payload: PaymentUpdate,
    _: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    entity = await db.get(Payment, payment_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Payment not found")
    return await Repository(Payment, db).update(entity, values(payload))


@router.delete("/payments/{payment_id}", status_code=204, tags=["payments"])
async def delete_payment(
    payment_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    entity = await db.get(Payment, payment_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Payment not found")
    await Repository(Payment, db).delete(entity)


@router.get("/reviews", response_model=list[ReviewRead], tags=["reviews"])
async def list_reviews(
    booking_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Review).order_by(Review.created_at.desc()).limit(limit).offset(offset)
    if booking_id:
        query = query.where(Review.booking_id == booking_id)
    return list((await db.scalars(query)).all())


@router.post("/reviews", response_model=ReviewRead, status_code=201, tags=["reviews"])
async def create_review(payload: ReviewCreate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    booking = await ensure_booking_access(db, current, payload.booking_id)
    if not is_admin(current) and payload.customer_id != current.id:
        raise HTTPException(status_code=403, detail="Reviews can only be created for yourself")
    if not is_admin(current) and booking.customer_id != current.id:
        raise HTTPException(status_code=403, detail="Only the booking customer can review")
    return await Repository(Review, db).create(values(payload))


@router.get("/reviews/{review_id}", response_model=ReviewRead, tags=["reviews"])
async def get_review(review_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ensure_review_access(db, current, review_id)


@router.patch("/reviews/{review_id}", response_model=ReviewRead, tags=["reviews"])
async def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entity = await ensure_review_access(db, current, review_id)
    return await Repository(Review, db).update(entity, values(payload))


@router.delete("/reviews/{review_id}", status_code=204, tags=["reviews"])
async def delete_review(review_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await ensure_review_access(db, current, review_id)
    await Repository(Review, db).delete(entity)


@router.get("/notifications", response_model=list[NotificationRead], tags=["notifications"])
async def list_notifications(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    if not is_admin(current):
        query = query.where(Notification.user_id == current.id)
    return list((await db.scalars(query)).all())


@router.post("/notifications", response_model=NotificationRead, status_code=201, tags=["notifications"])
async def create_notification(
    payload: NotificationCreate,
    _: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    return await Repository(Notification, db).create(values(payload))


@router.get("/notifications/{notification_id}", response_model=NotificationRead, tags=["notifications"])
async def get_notification(notification_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Notification, notification_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not is_admin(current) and entity.user_id != current.id:
        raise HTTPException(status_code=403, detail="Notification access denied")
    return entity


@router.patch("/notifications/{notification_id}", response_model=NotificationRead, tags=["notifications"])
async def update_notification(
    notification_id: uuid.UUID,
    payload: NotificationUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entity = await db.get(Notification, notification_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not is_admin(current) and entity.user_id != current.id:
        raise HTTPException(status_code=403, detail="Notification access denied")
    data = values(payload)
    if data.get("status") == "read" and "read_at" not in data:
        data["read_at"] = datetime.now(timezone.utc)
    return await Repository(Notification, db).update(entity, data)


@router.delete("/notifications/{notification_id}", status_code=204, tags=["notifications"])
async def delete_notification(notification_id: uuid.UUID, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity = await db.get(Notification, notification_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not is_admin(current) and entity.user_id != current.id:
        raise HTTPException(status_code=403, detail="Notification access denied")
    await Repository(Notification, db).delete(entity)