import asyncio
import secrets
from decimal import Decimal

from sqlalchemy import select

from .db import SessionLocal
from .models import (
    LotStatus,
    Owner,
    ParkingLot,
    ParkingLevel,
    ParkingSlot,
    ParkingZone,
    SlotStatus,
    StaffAssignment,
    User,
    UserRole,
    Vehicle,
)


async def seed() -> None:
    async with SessionLocal() as db:
        owner = await db.scalar(select(User).where(User.phone == "+919900000001"))
        if not owner:
            owner = User(
                email="owner.demo@parken.local",
                password_hash=secrets.token_urlsafe(48),
                full_name="Aarav Mehta",
                phone="+919900000001",
                role=UserRole.owner,
            )
            db.add(owner)
            await db.flush()
            owner_profile = Owner(user_id=owner.id, business_name="ORT Bengaluru", verified=True)
            db.add(owner_profile)
            await db.flush()
        else:
            owner_profile = await db.scalar(select(Owner).where(Owner.user_id == owner.id))
            if not owner_profile:
                owner_profile = Owner(user_id=owner.id, business_name="ORT Bengaluru", verified=True)
                db.add(owner_profile)
                await db.flush()

        existing_lot = await db.scalar(
            select(ParkingLot.id).where(ParkingLot.owner_id == owner_profile.id).limit(1)
        )
        if existing_lot:
            print("ORT demo inventory already exists; no changes made.")
            return

        places = [
            {
                "name": "Orchard Central Parking",
                "address": "100 Feet Road, Indiranagar",
                "city": "Bengaluru",
                "latitude": Decimal("12.971600"),
                "longitude": Decimal("77.641200"),
                "parking_type": "mall",
                "parking_mode": "paid",
                "rate": Decimal("60.00"),
                "slots": 18,
            },
            {
                "name": "St. Martha’s Hospital",
                "address": "Nrupathunga Road, Sampangi Rama Nagar",
                "city": "Bengaluru",
                "latitude": Decimal("12.969800"),
                "longitude": Decimal("77.591200"),
                "parking_type": "hospital",
                "parking_mode": "hybrid",
                "rate": Decimal("30.00"),
                "slots": 24,
            },
            {
                "name": "Kempegowda Airport · P2",
                "address": "Terminal Boulevard, Devanahalli",
                "city": "Bengaluru",
                "latitude": Decimal("13.198600"),
                "longitude": Decimal("77.706600"),
                "parking_type": "airport",
                "parking_mode": "paid",
                "rate": Decimal("100.00"),
                "slots": 40,
            },
            {
                "name": "Olive Street Valet",
                "address": "12th Main Road, Indiranagar",
                "city": "Bengaluru",
                "latitude": Decimal("12.978100"),
                "longitude": Decimal("77.640800"),
                "parking_type": "valet",
                "parking_mode": "valet",
                "rate": Decimal("120.00"),
                "slots": 10,
            },
            {
                "name": "Cubbon Park Visitor Parking",
                "address": "Kasturba Road, Ashok Nagar",
                "city": "Bengaluru",
                "latitude": Decimal("12.975200"),
                "longitude": Decimal("77.596300"),
                "parking_type": "event",
                "parking_mode": "free",
                "rate": Decimal("0.00"),
                "slots": 14,
            },
        ]
        for place in places:
            slot_count = place.pop("slots")
            hourly_rate = place.pop("rate")
            lot = ParkingLot(
                owner_id=owner_profile.id,
                status=LotStatus.active,
                identification_method="qr_code",
                is_closed=False,
                description="Secure, monitored parking with a fast digital check-in.",
                **place,
            )
            db.add(lot)
            await db.flush()
            categories = ["regular", "regular", "ev", "disabled", "visitor"]
            structure = {}
            for level_number in range((slot_count + 11) // 12):
                level = ParkingLevel(
                    parking_lot_id=lot.id,
                    level_code=f"L{level_number}",
                    display_name=f"Level {level_number}",
                    sort_order=level_number,
                )
                db.add(level)
                await db.flush()
                zone_code = chr(65 + level_number)
                zone = ParkingZone(
                    parking_level_id=level.id,
                    zone_code=zone_code,
                    display_name=f"Zone {zone_code} · Level {level_number}",
                )
                db.add(zone)
                await db.flush()
                structure[level_number] = (level, zone)
            for number in range(1, slot_count + 1):
                level_number = (number - 1) // 12
                level, zone = structure[level_number]
                db.add(
                    ParkingSlot(
                        parking_lot_id=lot.id,
                        slot_number=f"P{number:02d}",
                        hourly_rate=hourly_rate,
                        status=SlotStatus.available,
                        category=categories[(number - 1) % len(categories)],
                        level_name=level.level_code,
                        zone_name=zone.zone_code,
                        level_id=level.id,
                        zone_id=zone.id,
                    )
                )

        staff = await db.scalar(select(User).where(User.phone == "+919900000002"))
        if not staff:
            staff = User(
                email="staff.demo@parken.local",
                password_hash=secrets.token_urlsafe(48),
                full_name="Nisha Kumar",
                phone="+919900000002",
                role=UserRole.staff,
            )
            db.add(staff)
            await db.flush()
        first_lot = await db.scalar(
            select(ParkingLot).where(ParkingLot.owner_id == owner_profile.id).order_by(ParkingLot.name).limit(1)
        )
        if first_lot and not await db.scalar(
            select(StaffAssignment.id).where(
                StaffAssignment.staff_user_id == staff.id,
                StaffAssignment.parking_lot_id == first_lot.id,
            )
        ):
            db.add(StaffAssignment(staff_user_id=staff.id, parking_lot_id=first_lot.id))

        customer = await db.scalar(select(User).where(User.phone == "+919900000003"))
        if not customer:
            customer = User(
                email="driver.demo@parken.local",
                password_hash=secrets.token_urlsafe(48),
                full_name="Ishita Rao",
                phone="+919900000003",
                role=UserRole.customer,
            )
            db.add(customer)
            await db.flush()
        if not await db.scalar(select(Vehicle.id).where(Vehicle.user_id == customer.id)):
            db.add(
                Vehicle(
                    user_id=customer.id,
                    plate_number="KA 03 MN 2486",
                    normalized_plate="KA03MN2486",
                    label="White sedan",
                    vehicle_type="car",
                    is_default=True,
                )
            )
        await db.commit()
        print("Seeded five Bengaluru parking locations, demo roles, a vehicle, and staff access.")


if __name__ == "__main__":
    asyncio.run(seed())
