import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDTimestampMixin


class ParkingLevel(UUIDTimestampMixin, Base):
    __tablename__ = "parking_levels"
    __table_args__ = (
        UniqueConstraint("parking_lot_id", "level_code", name="uq_lot_level_code"),
    )

    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parking_lots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_code: Mapped[str] = mapped_column(String(24), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ParkingZone(UUIDTimestampMixin, Base):
    __tablename__ = "parking_zones"
    __table_args__ = (
        UniqueConstraint("parking_level_id", "zone_code", name="uq_level_zone_code"),
    )

    parking_level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parking_levels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_code: Mapped[str] = mapped_column(String(24), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
