import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDTimestampMixin


class UserRole(str, enum.Enum):
    customer = "customer"
    staff = "staff"
    owner = "owner"
    admin = "admin"


class AccountStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    deleted = "deleted"


class LotStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class SlotStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    maintenance = "maintenance"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class ReviewStatus(str, enum.Enum):
    published = "published"
    hidden = "hidden"


class NotificationStatus(str, enum.Enum):
    unread = "unread"
    read = "read"


class User(UUIDTimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.customer, nullable=False, index=True
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status"), default=AccountStatus.active, nullable=False
    )

    owner_profile: Mapped["Owner | None"] = relationship(back_populates="user", uselist=False)
    admin_profile: Mapped["Admin | None"] = relationship(back_populates="user", uselist=False)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")
    reviews: Mapped[list["Review"]] = relationship(back_populates="customer")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


class Owner(UUIDTimestampMixin, Base):
    __tablename__ = "owners"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    business_name: Mapped[str | None] = mapped_column(String(200))
    government_id: Mapped[str | None] = mapped_column(String(120))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="owner_profile")
    parking_lots: Mapped[list["ParkingLot"]] = relationship(back_populates="owner")


class Admin(UUIDTimestampMixin, Base):
    __tablename__ = "admins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="admin_profile")


class ParkingLot(UUIDTimestampMixin, Base):
    __tablename__ = "parking_lots"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parking_type: Mapped[str] = mapped_column(
        String(24), default="mall", server_default="mall", nullable=False
    )
    parking_mode: Mapped[str] = mapped_column(
        String(24), default="paid", server_default="paid", nullable=False
    )
    identification_method: Mapped[str] = mapped_column(
        String(24), default="qr_code", server_default="qr_code", nullable=False
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    closure_message: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, name="lot_status"), default=LotStatus.draft, nullable=False, index=True
    )

    owner: Mapped[Owner] = relationship(back_populates="parking_lots")
    slots: Mapped[list["ParkingSlot"]] = relationship(
        back_populates="parking_lot", cascade="all, delete-orphan"
    )


class ParkingSlot(UUIDTimestampMixin, Base):
    __tablename__ = "parking_slots"
    __table_args__ = (UniqueConstraint("parking_lot_id", "slot_number", name="uq_lot_slot_number"),)

    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_lots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_number: Mapped[str] = mapped_column(String(40), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(40), default="car", nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(
        String(24), default="regular", server_default="regular", nullable=False
    )
    level_name: Mapped[str | None] = mapped_column(String(40))
    zone_name: Mapped[str | None] = mapped_column(String(40))
    level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parking_levels.id", ondelete="SET NULL", name="fk_parking_slots_level_id"),
        index=True,
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parking_zones.id", ondelete="SET NULL", name="fk_parking_slots_zone_id"),
        index=True,
    )
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, name="slot_status"), default=SlotStatus.available, nullable=False, index=True
    )

    parking_lot: Mapped[ParkingLot] = relationship(back_populates="slots")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="parking_slot")


class Booking(UUIDTimestampMixin, Base):
    __tablename__ = "bookings"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parking_slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_slots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    corporate_pass_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corporate_passes.id", ondelete="SET NULL"),
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), default=BookingStatus.pending, nullable=False, index=True
    )

    customer: Mapped[User] = relationship(back_populates="bookings")
    parking_slot: Mapped[ParkingSlot] = relationship(back_populates="bookings")
    payment: Mapped["Payment | None"] = relationship(back_populates="booking", uselist=False)
    reviews: Mapped[list["Review"]] = relationship(back_populates="booking")


class Payment(UUIDTimestampMixin, Base):
    __tablename__ = "payments"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(60))
    provider_reference: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.pending, nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="payment")


class Review(UUIDTimestampMixin, Base):
    __tablename__ = "reviews"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"), default=ReviewStatus.published, nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="reviews")
    customer: Mapped[User] = relationship(back_populates="reviews")


class Notification(UUIDTimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.unread,
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="notifications")