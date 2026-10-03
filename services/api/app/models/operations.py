import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDTimestampMixin


class OtpChallenge(UUIDTimestampMixin, Base):
    __tablename__ = "otp_challenges"
    __table_args__ = (Index("ix_otp_challenges_phone_created", "phone", "created_at"),)

    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150))
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Vehicle(UUIDTimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (Index("uq_vehicles_normalized_plate", "normalized_plate", unique=True),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    normalized_plate: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(60), default="My vehicle", nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(24), default="car", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class StaffAssignment(UUIDTimestampMixin, Base):
    __tablename__ = "staff_assignments"
    __table_args__ = (Index("uq_staff_lot_assignment", "staff_user_id", "parking_lot_id", unique=True),)

    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_lots.id", ondelete="CASCADE"), nullable=False, index=True
    )


class ParkingSession(UUIDTimestampMixin, Base):
    __tablename__ = "parking_sessions"
    __table_args__ = (
        Index(
            "uq_parking_sessions_active_slot",
            "parking_slot_id",
            unique=True,
            postgresql_where=text("status = 'active' AND parking_slot_id IS NOT NULL"),
        ),
        Index(
            "uq_parking_sessions_active_vehicle",
            "vehicle_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_parking_sessions_vehicle_status", "vehicle_id", "status"),
    )

    public_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    qr_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parking_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_slots.id", ondelete="RESTRICT"), index=True
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    entry_method: Mapped[str] = mapped_column(String(16), default="online", nullable=False)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valet_status: Mapped[str] = mapped_column(
        String(24), default="standard", server_default="standard", nullable=False
    )
    valet_handover_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valet_retrieval_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valet_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emergency_priority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    slot_override: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    override_reason: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)


class Incident(UUIDTimestampMixin, Base):
    __tablename__ = "incidents"

    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_lots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parking_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_sessions.id", ondelete="SET NULL")
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False, index=True)


class CorporatePass(UUIDTimestampMixin, Base):
    __tablename__ = "corporate_passes"

    pass_code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_lots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    holder_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL")
    )
    pass_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    visitor_name: Mapped[str | None] = mapped_column(String(150))
    visitor_phone: Mapped[str | None] = mapped_column(String(32))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
