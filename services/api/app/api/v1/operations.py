import hashlib
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ...dependencies import get_current_user, require_roles
from ...models import (
    Booking,
    BookingStatus,
    CorporatePass,
    Incident,
    LotStatus,
    Owner,
    ParkingLot,
    ParkingLevel,
    ParkingSession,
    ParkingSlot,
    ParkingZone,
    SlotStatus,
    StaffAssignment,
    User,
    UserRole,
    Vehicle,
)
from ...schemas import (
    BookingCreate,
    BookingRead,
    CorporatePassCreate,
    CorporatePassRead,
    CorporateReservationCreate,
    EmergencyPriorityUpdate,
    IncidentCreate,
    IncidentRead,
    ParkingSearchRead,
    ParkingLevelRead,
    ParkingZoneRead,
    ParkingLotRead,
    ParkingSessionAssign,
    ParkingSessionCreate,
    ParkingSessionCreated,
    ParkingSessionRead,
    StaffAssignmentCreate,
    VehicleCreate,
    VehicleRead,
)
from ...services.booking_service import create_booking

router = APIRouter(tags=["parking operations"])
SessionDB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def can_operate_lot(db: AsyncSession, user: User, lot: ParkingLot) -> bool:
    if user.role == UserRole.admin:
        return True
    if user.role == UserRole.owner:
        return bool(
            await db.scalar(
                select(Owner.id).where(Owner.id == lot.owner_id, Owner.user_id == user.id)
            )
        )
    if user.role == UserRole.staff:
        return bool(
            await db.scalar(
                select(StaffAssignment.id).where(
                    StaffAssignment.staff_user_id == user.id,
                    StaffAssignment.parking_lot_id == lot.id,
                )
            )
        )
    return False


def normalize_plate(plate: str) -> str:
    return "".join(character for character in plate.upper() if character.isalnum())


@router.get("/parking/search", response_model=list[ParkingSearchRead])
async def search_parking(
    db: SessionDB,
    q: str | None = None,
    city: str | None = None,
    parking_type: str | None = None,
    parking_mode: str | None = None,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=100),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ParkingSearchRead]:
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="latitude and longitude must be provided together")
    now = datetime.now(timezone.utc)
    query = (
        select(ParkingLot, func.count(ParkingSlot.id), func.min(ParkingSlot.hourly_rate))
        .outerjoin(
            ParkingSlot,
            (ParkingSlot.parking_lot_id == ParkingLot.id)
            & (ParkingSlot.status == SlotStatus.available),
        )
        .outerjoin(
            Booking,
            (Booking.parking_slot_id == ParkingSlot.id)
            & (Booking.status.in_((BookingStatus.pending, BookingStatus.confirmed)))
            & (Booking.starts_at <= now)
            & (Booking.ends_at > now),
        )
        .where(
            ParkingLot.status == LotStatus.active,
            ParkingLot.is_closed.is_(False),
            Booking.id.is_(None),
        )
        .group_by(ParkingLot.id)
        .order_by(ParkingLot.name)
    )
    if latitude is not None and longitude is not None:
        latitude_delta = radius_km / 110.574
        longitude_delta = min(180, radius_km / max(0.01, 111.320 * abs(math.cos(math.radians(latitude)))))
        query = query.where(
            ParkingLot.latitude.between(latitude - latitude_delta, latitude + latitude_delta),
            ParkingLot.longitude.between(longitude - longitude_delta, longitude + longitude_delta),
        ).limit(min(limit * 8, 800))
    else:
        query = query.limit(limit)
    if city:
        query = query.where(func.lower(ParkingLot.city) == city.strip().lower())
    if parking_type:
        query = query.where(ParkingLot.parking_type == parking_type)
    if parking_mode:
        query = query.where(ParkingLot.parking_mode == parking_mode)
    if q:
        term = f"%{q.strip().lower()}%"
        query = query.where(
            func.lower(ParkingLot.name).like(term)
            | func.lower(ParkingLot.address).like(term)
            | func.lower(ParkingLot.city).like(term)
        )
    records = (await db.execute(query)).all()
    results: list[ParkingSearchRead] = []
    distances: dict[uuid.UUID, float] = {}
    for lot, available, starting_rate in records:
        if latitude is not None and longitude is not None:
            lat1, lat2 = math.radians(latitude), math.radians(float(lot.latitude))
            delta_lat = lat2 - lat1
            delta_lon = math.radians(float(lot.longitude) - longitude)
            distance = 6371 * 2 * math.asin(
                math.sqrt(
                    math.sin(delta_lat / 2) ** 2
                    + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
                )
            )
            if distance > radius_km:
                continue
            distances[lot.id] = distance
        lot_data = {
            field: getattr(lot, field)
            for field in (
                "id", "owner_id", "name", "address", "city", "latitude", "longitude",
                "description", "status", "parking_type", "parking_mode", "identification_method",
                "is_closed", "closure_message", "created_at", "updated_at",
            )
        }
        results.append(ParkingSearchRead(**lot_data, available_slots=available, starting_hourly_rate=starting_rate))
    if latitude is not None and longitude is not None:
        results.sort(key=lambda item: distances[item.id])
    return results[:limit]


@router.get("/parking-lots/{lot_id}/levels", response_model=list[ParkingLevelRead])
async def list_parking_levels(
    lot_id: uuid.UUID,
    db: SessionDB,
    _: CurrentUser,
) -> list[ParkingLevelRead]:
    if not await db.get(ParkingLot, lot_id):
        raise HTTPException(status_code=404, detail="Parking location not found")
    levels = list(
        await db.scalars(
            select(ParkingLevel)
            .where(ParkingLevel.parking_lot_id == lot_id)
            .order_by(ParkingLevel.sort_order, ParkingLevel.level_code)
        )
    )
    zones = list(
        await db.scalars(
            select(ParkingZone)
            .join(ParkingLevel, ParkingZone.parking_level_id == ParkingLevel.id)
            .where(ParkingLevel.parking_lot_id == lot_id)
            .order_by(ParkingZone.zone_code)
        )
    )
    zones_by_level: dict[uuid.UUID, list[ParkingZoneRead]] = {}
    for zone in zones:
        zones_by_level.setdefault(zone.parking_level_id, []).append(
            ParkingZoneRead.model_validate(zone)
        )
    return [
        ParkingLevelRead(
            **{
                "id": level.id,
                "parking_lot_id": level.parking_lot_id,
                "level_code": level.level_code,
                "display_name": level.display_name,
                "sort_order": level.sort_order,
            },
            zones=zones_by_level.get(level.id, []),
        )
        for level in levels
    ]


@router.get("/vehicles", response_model=list[VehicleRead])
async def list_vehicles(db: SessionDB, user: CurrentUser) -> list[Vehicle]:
    return list(
        await db.scalars(
            select(Vehicle).where(Vehicle.user_id == user.id).order_by(Vehicle.is_default.desc())
        )
    )


@router.post("/vehicles", response_model=VehicleRead, status_code=201)
async def add_vehicle(payload: VehicleCreate, db: SessionDB, user: CurrentUser) -> Vehicle:
    plate = normalize_plate(payload.plate_number)
    if await db.scalar(select(Vehicle.id).where(Vehicle.normalized_plate == plate)):
        raise HTTPException(status_code=409, detail="That vehicle is already registered")
    if payload.is_default:
        await db.execute(
            Vehicle.__table__.update()
            .where(Vehicle.user_id == user.id)
            .values(is_default=False)
        )
    elif not await db.scalar(select(Vehicle.id).where(Vehicle.user_id == user.id)):
        payload.is_default = True
    vehicle = Vehicle(
        user_id=user.id,
        plate_number=payload.plate_number.upper().strip(),
        normalized_plate=plate,
        label=payload.label,
        vehicle_type=payload.vehicle_type,
        is_default=payload.is_default,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.delete("/vehicles/{vehicle_id}", status_code=204)
async def delete_vehicle(vehicle_id: uuid.UUID, db: SessionDB, user: CurrentUser) -> None:
    vehicle = await db.scalar(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.user_id == user.id)
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if await db.scalar(
        select(ParkingSession.id).where(
            ParkingSession.vehicle_id == vehicle.id, ParkingSession.status == "active"
        )
    ):
        raise HTTPException(status_code=409, detail="A vehicle with an active session cannot be removed")
    await db.delete(vehicle)
    await db.commit()


@router.post("/parking-sessions", response_model=ParkingSessionCreated, status_code=201)
async def create_parking_session(
    payload: ParkingSessionCreate,
    db: SessionDB,
    user: CurrentUser,
) -> ParkingSessionCreated:
    lot = await db.get(ParkingLot, payload.parking_lot_id)
    if not lot or lot.status != LotStatus.active or lot.is_closed:
        raise HTTPException(status_code=404, detail="Parking is not currently available")
    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if user.role == UserRole.customer:
        if vehicle.user_id != user.id:
            raise HTTPException(status_code=403, detail="You can only start a session for your vehicle")
        if not payload.parking_slot_id:
            raise HTTPException(status_code=422, detail="Choose an available slot to start a walk-in session")
    elif not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    if payload.emergency_priority:
        if user.role == UserRole.customer:
            raise HTTPException(status_code=403, detail="Emergency priority must be granted by parking staff")
        if lot.parking_type != "hospital" or not payload.override_reason:
            raise HTTPException(
                status_code=422,
                detail="Hospital emergency sessions require an override reason",
            )
    elif payload.override_reason:
        raise HTTPException(status_code=422, detail="An override reason requires emergency priority")

    slot = None
    if payload.parking_slot_id:
        slot = await db.scalar(
            select(ParkingSlot)
            .where(
                ParkingSlot.id == payload.parking_slot_id,
                ParkingSlot.parking_lot_id == lot.id,
            )
            .with_for_update()
        )
        if not slot or slot.status != SlotStatus.available:
            raise HTTPException(status_code=409, detail="That parking slot is not available")
        slot.status = SlotStatus.occupied

    token = secrets.token_urlsafe(32)
    session = ParkingSession(
        public_id=secrets.token_hex(6).upper(),
        qr_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        parking_lot_id=lot.id,
        parking_slot_id=slot.id if slot else None,
        vehicle_id=vehicle.id,
        customer_id=vehicle.user_id,
        staff_user_id=user.id if user.role in (UserRole.staff, UserRole.owner) else None,
        status="active",
        entry_method=payload.entry_method,
        valet_status="awaiting_handover" if lot.parking_type == "valet" else "standard",
        emergency_priority=payload.emergency_priority,
        override_reason=payload.override_reason,
        notes=payload.notes,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ParkingSessionCreated(
        **ParkingSessionRead.model_validate(session).model_dump(),
        qr_token=token,
    )


@router.get("/parking-sessions", response_model=list[ParkingSessionRead])
async def list_parking_sessions(
    db: SessionDB,
    user: CurrentUser,
    status: str | None = Query(default=None, pattern="^(active|closed)$"),
) -> list[ParkingSession]:
    query = select(ParkingSession)
    if user.role == UserRole.customer:
        query = query.where(ParkingSession.customer_id == user.id)
    elif user.role == UserRole.staff:
        assigned_lots = select(StaffAssignment.parking_lot_id).where(
            StaffAssignment.staff_user_id == user.id
        )
        query = query.where(ParkingSession.parking_lot_id.in_(assigned_lots))
    elif user.role == UserRole.owner:
        owner = await db.scalar(select(Owner).where(Owner.user_id == user.id))
        if not owner:
            return []
        owned_lots = select(ParkingLot.id).where(ParkingLot.owner_id == owner.id)
        query = query.where(ParkingSession.parking_lot_id.in_(owned_lots))
    if status:
        query = query.where(ParkingSession.status == status)
    return list(await db.scalars(query.order_by(ParkingSession.entry_at.desc()).limit(100)))


@router.post("/parking-sessions/{session_id}/assign", response_model=ParkingSessionRead)
async def assign_session_slot(
    session_id: uuid.UUID,
    payload: ParkingSessionAssign,
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.staff, UserRole.owner, UserRole.admin))],
) -> ParkingSession:
    session = await db.scalar(
        select(ParkingSession).where(ParkingSession.id == session_id).with_for_update()
    )
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Active parking session not found")
    lot = await db.get(ParkingLot, session.parking_lot_id)
    if not lot or not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    slot = await db.scalar(
        select(ParkingSlot)
        .where(
            ParkingSlot.id == payload.parking_slot_id,
            ParkingSlot.parking_lot_id == session.parking_lot_id,
        )
        .with_for_update()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")
    if slot.status != SlotStatus.available:
        if not (
            session.emergency_priority
            and lot.parking_type == "hospital"
            and slot.status == SlotStatus.maintenance
            and payload.override_reason
        ):
            raise HTTPException(status_code=409, detail="That parking slot is not available")
        session.override_reason = payload.override_reason
    maintenance_override = slot.status == SlotStatus.maintenance
    if session.parking_slot_id:
        previous = await db.get(ParkingSlot, session.parking_slot_id)
        if previous:
            previous.status = SlotStatus.maintenance if session.slot_override else SlotStatus.available
    slot.status = SlotStatus.occupied
    session.parking_slot_id = slot.id
    session.staff_user_id = user.id
    session.slot_override = maintenance_override
    await db.commit()
    await db.refresh(session)
    return session


@router.patch("/parking-sessions/{session_id}/priority", response_model=ParkingSessionRead)
async def set_emergency_priority(
    session_id: uuid.UUID,
    payload: EmergencyPriorityUpdate,
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.staff, UserRole.owner, UserRole.admin))],
) -> ParkingSession:
    session = await db.scalar(
        select(ParkingSession).where(ParkingSession.id == session_id).with_for_update()
    )
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Active parking session not found")
    lot = await db.get(ParkingLot, session.parking_lot_id)
    if not lot or lot.parking_type != "hospital":
        raise HTTPException(status_code=422, detail="Emergency priority is only available at hospitals")
    if not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    session.emergency_priority = payload.emergency_priority
    if payload.emergency_priority:
        session.override_reason = payload.override_reason
    elif not session.slot_override:
        session.override_reason = None
    session.staff_user_id = user.id
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/parking-sessions/{session_id}/valet/handover", response_model=ParkingSessionRead)
async def valet_handover(
    session_id: uuid.UUID,
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.staff, UserRole.owner, UserRole.admin))],
) -> ParkingSession:
    session = await db.scalar(
        select(ParkingSession).where(ParkingSession.id == session_id).with_for_update()
    )
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Active parking session not found")
    lot = await db.get(ParkingLot, session.parking_lot_id)
    if not lot or lot.parking_type != "valet":
        raise HTTPException(status_code=422, detail="This session is not a valet service")
    if not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    if session.valet_status != "awaiting_handover":
        raise HTTPException(status_code=409, detail="Vehicle handover has already been recorded")
    session.valet_status = "parked"
    session.valet_handover_at = datetime.now(timezone.utc)
    session.staff_user_id = user.id
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/parking-sessions/{session_id}/valet/retrieval", response_model=ParkingSessionRead)
async def request_valet_retrieval(
    session_id: uuid.UUID,
    db: SessionDB,
    user: CurrentUser,
) -> ParkingSession:
    session = await db.scalar(
        select(ParkingSession).where(ParkingSession.id == session_id).with_for_update()
    )
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Active parking session not found")
    lot = await db.get(ParkingLot, session.parking_lot_id)
    if not lot or lot.parking_type != "valet":
        raise HTTPException(status_code=422, detail="This session is not a valet service")
    if user.role == UserRole.customer:
        if session.customer_id != user.id:
            raise HTTPException(status_code=403, detail="You cannot request this vehicle")
    elif not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    if session.valet_status != "parked":
        raise HTTPException(status_code=409, detail="The vehicle is not ready for retrieval")
    session.valet_status = "retrieval_requested"
    session.valet_retrieval_requested_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/parking-sessions/{session_id}/valet/complete-retrieval", response_model=ParkingSessionRead)
async def complete_valet_retrieval(
    session_id: uuid.UUID,
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.staff, UserRole.owner, UserRole.admin))],
) -> ParkingSession:
    session = await db.scalar(
        select(ParkingSession).where(ParkingSession.id == session_id).with_for_update()
    )
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Active parking session not found")
    lot = await db.get(ParkingLot, session.parking_lot_id)
    if not lot or lot.parking_type != "valet":
        raise HTTPException(status_code=422, detail="This session is not a valet service")
    if not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    if session.valet_status != "retrieval_requested":
        raise HTTPException(status_code=409, detail="A retrieval request is required")
    session.valet_status = "retrieved"
    session.valet_retrieved_at = datetime.now(timezone.utc)
    session.staff_user_id = user.id
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/parking-sessions/{session_id}/close", response_model=ParkingSessionRead)
async def close_parking_session(
    session_id: uuid.UUID,
    db: SessionDB,
    user: CurrentUser,
) -> ParkingSession:
    session = await db.scalar(
        select(ParkingSession).where(ParkingSession.id == session_id).with_for_update()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Parking session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Parking session is already closed")
    if user.role == UserRole.customer:
        if session.customer_id != user.id:
            raise HTTPException(status_code=403, detail="You cannot close this parking session")
    else:
        lot = await db.get(ParkingLot, session.parking_lot_id)
        if not lot or not await can_operate_lot(db, user, lot):
            raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    lot = await db.get(ParkingLot, session.parking_lot_id)
    if lot and lot.parking_type == "valet" and session.valet_status != "retrieved":
        raise HTTPException(status_code=409, detail="Complete the valet retrieval before closing this session")
    session.status = "closed"
    session.exit_at = datetime.now(timezone.utc)
    session.synced_at = session.exit_at
    if session.parking_slot_id:
        slot = await db.get(ParkingSlot, session.parking_slot_id)
        if slot and slot.status == SlotStatus.occupied:
            slot.status = SlotStatus.maintenance if session.slot_override else SlotStatus.available
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/parking-sessions/lookup", response_model=ParkingSessionRead)
async def lookup_parking_session(
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.staff, UserRole.owner, UserRole.admin))],
    parking_lot_id: uuid.UUID,
    method: str = Query(pattern="^(qr_code|session_id|vehicle_number)$"),
    value: str = Query(min_length=3, max_length=80),
) -> ParkingSession:
    lot = await db.get(ParkingLot, parking_lot_id)
    if not lot or not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You are not assigned to this parking location")
    query = select(ParkingSession).where(
        ParkingSession.parking_lot_id == lot.id,
        ParkingSession.status == "active",
    )
    if method == "qr_code":
        query = query.where(
            ParkingSession.qr_token_hash == hashlib.sha256(value.encode()).hexdigest()
        )
    elif method == "session_id":
        query = query.where(ParkingSession.public_id == value.upper())
    else:
        vehicle_ids = select(Vehicle.id).where(
            Vehicle.normalized_plate == normalize_plate(value)
        )
        query = query.where(ParkingSession.vehicle_id.in_(vehicle_ids))
    session = await db.scalar(query)
    if not session:
        raise HTTPException(status_code=404, detail="No active parking session found")
    return session


@router.post("/incidents", response_model=IncidentRead, status_code=201)
async def report_incident(
    payload: IncidentCreate,
    db: SessionDB,
    user: CurrentUser,
) -> Incident:
    lot = await db.get(ParkingLot, payload.parking_lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Parking location not found")
    if payload.parking_session_id:
        session = await db.get(ParkingSession, payload.parking_session_id)
        if not session or session.parking_lot_id != lot.id:
            raise HTTPException(status_code=404, detail="Parking session not found")
        if user.role == UserRole.customer and session.customer_id != user.id:
            raise HTTPException(status_code=403, detail="You cannot report against this session")
    incident = Incident(
        parking_lot_id=lot.id,
        reporter_id=user.id,
        parking_session_id=payload.parking_session_id,
        category=payload.category,
        description=payload.description,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


@router.post("/staff-assignments", status_code=201)
async def assign_staff_to_lot(
    payload: StaffAssignmentCreate,
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.owner, UserRole.admin))],
) -> dict[str, str]:
    lot = await db.get(ParkingLot, payload.parking_lot_id)
    staff = await db.get(User, payload.staff_user_id)
    if not lot or not staff:
        raise HTTPException(status_code=404, detail="Parking location or staff user not found")
    if staff.role != UserRole.staff:
        raise HTTPException(status_code=422, detail="The selected user does not have the staff role")
    if not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=403, detail="You cannot manage this parking location")
    assignment = StaffAssignment(
        staff_user_id=staff.id,
        parking_lot_id=lot.id,
    )
    db.add(assignment)
    await db.commit()
    return {"status": "assigned"}


@router.get("/corporate/passes", response_model=list[CorporatePassRead])
async def list_corporate_passes(
    db: SessionDB,
    user: CurrentUser,
) -> list[CorporatePass]:
    query = select(CorporatePass)
    if user.role == UserRole.customer:
        query = query.where(CorporatePass.holder_user_id == user.id)
    elif user.role == UserRole.staff:
        assigned_lots = select(StaffAssignment.parking_lot_id).where(
            StaffAssignment.staff_user_id == user.id
        )
        query = query.where(CorporatePass.parking_lot_id.in_(assigned_lots))
    elif user.role == UserRole.owner:
        owner = await db.scalar(select(Owner).where(Owner.user_id == user.id))
        if not owner:
            return []
        owned_lots = select(ParkingLot.id).where(ParkingLot.owner_id == owner.id)
        query = query.where(CorporatePass.parking_lot_id.in_(owned_lots))
    return list(await db.scalars(query.order_by(CorporatePass.created_at.desc()).limit(200)))


@router.get("/parking/managed-lots", response_model=list[ParkingLotRead])
async def list_managed_parking_lots(
    db: SessionDB,
    user: CurrentUser,
) -> list[ParkingLot]:
    query = select(ParkingLot).where(ParkingLot.status == LotStatus.active)
    if user.role == UserRole.owner:
        owner = await db.scalar(select(Owner).where(Owner.user_id == user.id))
        if not owner:
            return []
        query = query.where(ParkingLot.owner_id == owner.id)
    elif user.role == UserRole.staff:
        assignments = select(StaffAssignment.parking_lot_id).where(
            StaffAssignment.staff_user_id == user.id
        )
        query = query.where(ParkingLot.id.in_(assignments))
    elif user.role != UserRole.admin:
        return []
    return list(await db.scalars(query.order_by(ParkingLot.name)))


@router.get("/corporate/passes/lookup", response_model=CorporatePassRead)
async def lookup_corporate_pass(
    db: SessionDB,
    user: CurrentUser,
    parking_lot_id: uuid.UUID,
    pass_code: str = Query(min_length=8, max_length=24),
) -> CorporatePass:
    lot = await db.get(ParkingLot, parking_lot_id)
    if not lot or not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=404, detail="Parking location not found")
    now = datetime.now(timezone.utc)
    corporate_pass = await db.scalar(
        select(CorporatePass).where(
            CorporatePass.parking_lot_id == parking_lot_id,
            CorporatePass.pass_code == pass_code.strip().upper(),
            CorporatePass.status == "active",
            CorporatePass.starts_at <= now,
            (CorporatePass.expires_at.is_(None) | (CorporatePass.expires_at > now)),
        )
    )
    if not corporate_pass:
        raise HTTPException(status_code=404, detail="No active pass matches this code")
    return corporate_pass


@router.post("/corporate/passes", response_model=CorporatePassRead, status_code=201)
async def create_corporate_pass(
    payload: CorporatePassCreate,
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.owner, UserRole.admin))],
) -> CorporatePass:
    lot = await db.get(ParkingLot, payload.parking_lot_id)
    if not lot or not await can_operate_lot(db, user, lot):
        raise HTTPException(status_code=404, detail="Parking location not found")
    if payload.pass_type != "visitor" and lot.parking_type != "corporate":
        raise HTTPException(status_code=422, detail="Employee passes require a corporate parking location")
    if payload.holder_user_id:
        holder = await db.get(User, payload.holder_user_id)
        if not holder or holder.role != UserRole.customer or holder.status.value != "active":
            raise HTTPException(status_code=422, detail="Pass holder must be an active customer account")
    if payload.vehicle_id:
        vehicle = await db.get(Vehicle, payload.vehicle_id)
        if not vehicle or not payload.holder_user_id or vehicle.user_id != payload.holder_user_id:
            raise HTTPException(status_code=422, detail="Pass vehicle must belong to its account holder")
    corporate_pass = CorporatePass(
        pass_code=secrets.token_hex(6).upper(),
        parking_lot_id=lot.id,
        created_by=user.id,
        holder_user_id=payload.holder_user_id,
        vehicle_id=payload.vehicle_id,
        pass_type=payload.pass_type,
        visitor_name=payload.visitor_name,
        visitor_phone=payload.visitor_phone,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        status="active",
        notes=payload.notes,
    )
    db.add(corporate_pass)
    await db.commit()
    await db.refresh(corporate_pass)
    return corporate_pass


@router.post(
    "/corporate/passes/{pass_id}/reservations",
    response_model=BookingRead,
    status_code=201,
)
async def create_corporate_reservation(
    pass_id: uuid.UUID,
    payload: CorporateReservationCreate,
    db: SessionDB,
    user: CurrentUser,
) -> Booking:
    if user.role != UserRole.customer:
        raise HTTPException(status_code=403, detail="Reservations must be made by the pass holder")
    corporate_pass = await db.scalar(
        select(CorporatePass).where(CorporatePass.id == pass_id).with_for_update()
    )
    if not corporate_pass or corporate_pass.status != "active":
        raise HTTPException(status_code=404, detail="Active corporate pass not found")
    if corporate_pass.holder_user_id != user.id:
        raise HTTPException(status_code=403, detail="This pass is not assigned to your account")
    if payload.starts_at < corporate_pass.starts_at or (
        corporate_pass.expires_at and payload.ends_at > corporate_pass.expires_at
    ):
        raise HTTPException(status_code=422, detail="Reservation is outside the pass validity window")
    holder_id = corporate_pass.holder_user_id
    if not holder_id:
        raise HTTPException(status_code=422, detail="A visitor pass must be linked to an account before reservation")
    holder = await db.get(User, holder_id)
    if not holder or holder.role != UserRole.customer:
        raise HTTPException(status_code=422, detail="Pass holder is not eligible to reserve")
    vehicle_id = payload.vehicle_id or corporate_pass.vehicle_id
    if vehicle_id:
        vehicle = await db.get(Vehicle, vehicle_id)
        if not vehicle or vehicle.user_id != holder.id:
            raise HTTPException(status_code=422, detail="Reservation vehicle must belong to the pass holder")
    slot = await db.scalar(
        select(ParkingSlot)
        .where(
            ParkingSlot.id == payload.parking_slot_id,
            ParkingSlot.parking_lot_id == corporate_pass.parking_lot_id,
        )
        .with_for_update()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Parking slot not found at this location")
    if corporate_pass.pass_type == "executive" and slot.category != "vip":
        raise HTTPException(status_code=422, detail="Executive passes require a VIP slot")
    if corporate_pass.pass_type == "visitor" and slot.category != "visitor":
        raise HTTPException(status_code=422, detail="Visitor passes require a visitor slot")
    duration = Decimal(str((payload.ends_at - payload.starts_at).total_seconds())) / Decimal(3600)
    amount = (slot.hourly_rate * duration).quantize(Decimal("0.01"))
    booking_payload = BookingCreate(
        customer_id=holder.id,
        parking_slot_id=slot.id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        total_amount=amount,
    )
    return await create_booking(
        db,
        holder,
        booking_payload,
        corporate_pass_id=corporate_pass.id,
    )


@router.post("/corporate/passes/{pass_id}/revoke", response_model=CorporatePassRead)
async def revoke_corporate_pass(
    pass_id: uuid.UUID,
    db: SessionDB,
    user: CurrentUser,
) -> CorporatePass:
    corporate_pass = await db.get(CorporatePass, pass_id)
    if not corporate_pass:
        raise HTTPException(status_code=404, detail="Corporate pass not found")
    if user.role == UserRole.customer:
        if corporate_pass.holder_user_id != user.id:
            raise HTTPException(status_code=403, detail="This pass is not assigned to your account")
    else:
        lot = await db.get(ParkingLot, corporate_pass.parking_lot_id)
        if not lot or not await can_operate_lot(db, user, lot):
            raise HTTPException(status_code=403, detail="You cannot manage this corporate pass")
    if corporate_pass.status != "active":
        raise HTTPException(status_code=409, detail="Corporate pass is not active")
    corporate_pass.status = "revoked"
    await db.commit()
    await db.refresh(corporate_pass)
    return corporate_pass


@router.get("/owner/analytics")
async def owner_analytics(
    db: SessionDB,
    user: Annotated[User, Depends(require_roles(UserRole.owner, UserRole.admin))],
) -> dict[str, object]:
    owner = await db.scalar(select(Owner).where(Owner.user_id == user.id)) if user.role == UserRole.owner else None
    lots_query = select(ParkingLot.id)
    if owner:
        lots_query = lots_query.where(ParkingLot.owner_id == owner.id)
    lot_ids = list(await db.scalars(lots_query))
    if not lot_ids and user.role != UserRole.admin:
        return {
            "locations": 0,
            "capacity": 0,
            "occupied": 0,
            "occupancy_rate": 0,
            "revenue": "0.00",
            "bookings": 0,
            "peak_entry_hour": None,
            "overstay_sessions": 0,
        }
    slot_counts = await db.execute(
        select(func.count(ParkingSlot.id), func.count(ParkingSlot.id).filter(ParkingSlot.status == SlotStatus.occupied))
        .where(ParkingSlot.parking_lot_id.in_(lot_ids))
    )
    capacity, occupied = slot_counts.one()
    revenue = await db.scalar(
        select(func.coalesce(func.sum(Booking.total_amount), 0))
        .join(ParkingSlot, Booking.parking_slot_id == ParkingSlot.id)
        .where(ParkingSlot.parking_lot_id.in_(lot_ids), Booking.status.in_(("confirmed", "completed")))
    )
    booking_count = await db.scalar(
        select(func.count(Booking.id))
        .join(ParkingSlot, Booking.parking_slot_id == ParkingSlot.id)
        .where(ParkingSlot.parking_lot_id.in_(lot_ids))
    )
    overstay_count = await db.scalar(
        select(func.count(ParkingSession.id)).where(
            ParkingSession.parking_lot_id.in_(lot_ids),
            ParkingSession.status == "active",
            ParkingSession.entry_at <= datetime.now(timezone.utc) - timedelta(hours=12),
        )
    )
    peak_hour = await db.scalar(
        select(func.extract("hour", ParkingSession.entry_at))
        .where(ParkingSession.parking_lot_id.in_(lot_ids))
        .group_by(func.extract("hour", ParkingSession.entry_at))
        .order_by(func.count(ParkingSession.id).desc())
        .limit(1)
    )
    return {
        "locations": len(lot_ids),
        "capacity": capacity,
        "occupied": occupied,
        "occupancy_rate": round(occupied * 100 / capacity) if capacity else 0,
        "revenue": str(Decimal(revenue)),
        "bookings": booking_count,
        "peak_entry_hour": int(peak_hour) if peak_hour is not None else None,
        "overstay_sessions": overstay_count,
    }
