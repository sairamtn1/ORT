"""parking operations and phone OTP

Revision ID: ce17e981b4a2
Revises: b8bbb0854e9d
Create Date: 2026-10-02
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "ce17e981b4a2"
down_revision: str | None = "b8bbb0854e9d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'staff'")
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    op.add_column("parking_lots", sa.Column("parking_type", sa.String(24), server_default="mall", nullable=False))
    op.add_column("parking_lots", sa.Column("parking_mode", sa.String(24), server_default="paid", nullable=False))
    op.add_column("parking_lots", sa.Column("identification_method", sa.String(24), server_default="qr_code", nullable=False))
    op.add_column("parking_lots", sa.Column("is_closed", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("parking_lots", sa.Column("closure_message", sa.String(240), nullable=True))

    op.create_table(
        "parking_levels",
        sa.Column("parking_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level_code", sa.String(24), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parking_lot_id"], ["parking_lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parking_lot_id", "level_code", name="uq_lot_level_code"),
    )
    op.create_index("ix_parking_levels_parking_lot_id", "parking_levels", ["parking_lot_id"])
    op.create_table(
        "parking_zones",
        sa.Column("parking_level_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("zone_code", sa.String(24), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parking_level_id"], ["parking_levels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parking_level_id", "zone_code", name="uq_level_zone_code"),
    )
    op.create_index("ix_parking_zones_parking_level_id", "parking_zones", ["parking_level_id"])

    op.add_column("parking_slots", sa.Column("category", sa.String(24), server_default="regular", nullable=False))
    op.add_column("parking_slots", sa.Column("level_name", sa.String(40), nullable=True))
    op.add_column("parking_slots", sa.Column("zone_name", sa.String(40), nullable=True))
    op.add_column("parking_slots", sa.Column("level_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("parking_slots", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_parking_slots_level_id", "parking_slots", "parking_levels", ["level_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_parking_slots_zone_id", "parking_slots", "parking_zones", ["zone_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_parking_slots_level_id", "parking_slots", ["level_id"])
    op.create_index("ix_parking_slots_zone_id", "parking_slots", ["zone_id"])

    op.create_table(
        "otp_challenges",
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_challenges_phone_created", "otp_challenges", ["phone", "created_at"])

    op.create_table(
        "vehicles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_number", sa.String(20), nullable=False),
        sa.Column("normalized_plate", sa.String(20), nullable=False),
        sa.Column("label", sa.String(60), nullable=False),
        sa.Column("vehicle_type", sa.String(24), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicles_user_id", "vehicles", ["user_id"])
    op.create_index("uq_vehicles_normalized_plate", "vehicles", ["normalized_plate"], unique=True)

    op.create_table(
        "corporate_passes",
        sa.Column("pass_code", sa.String(24), nullable=False),
        sa.Column("parking_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pass_type", sa.String(24), nullable=False),
        sa.Column("visitor_name", sa.String(150), nullable=True),
        sa.Column("visitor_phone", sa.String(32), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parking_lot_id"], ["parking_lots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["holder_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_corporate_passes_pass_code", "corporate_passes", ["pass_code"], unique=True)
    op.create_index("ix_corporate_passes_parking_lot_id", "corporate_passes", ["parking_lot_id"])
    op.create_index("ix_corporate_passes_holder_user_id", "corporate_passes", ["holder_user_id"])
    op.create_index("ix_corporate_passes_pass_type", "corporate_passes", ["pass_type"])
    op.create_index("ix_corporate_passes_status", "corporate_passes", ["status"])
    op.add_column(
        "bookings",
        sa.Column("corporate_pass_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_bookings_corporate_pass_id",
        "bookings",
        "corporate_passes",
        ["corporate_pass_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_bookings_corporate_pass_id", "bookings", ["corporate_pass_id"])

    op.create_table(
        "staff_assignments",
        sa.Column("staff_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parking_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parking_lot_id"], ["parking_lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_assignments_staff_user_id", "staff_assignments", ["staff_user_id"])
    op.create_index("ix_staff_assignments_parking_lot_id", "staff_assignments", ["parking_lot_id"])
    op.create_index("uq_staff_lot_assignment", "staff_assignments", ["staff_user_id", "parking_lot_id"], unique=True)

    op.create_table(
        "parking_sessions",
        sa.Column("public_id", sa.String(16), nullable=False),
        sa.Column("qr_token_hash", sa.String(64), nullable=False),
        sa.Column("parking_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parking_slot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("entry_method", sa.String(16), nullable=False),
        sa.Column("entry_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("exit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valet_status", sa.String(24), server_default="standard", nullable=False),
        sa.Column("valet_handover_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valet_retrieval_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valet_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emergency_priority", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("slot_override", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("override_reason", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parking_lot_id"], ["parking_lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parking_slot_id"], ["parking_slots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parking_sessions_public_id", "parking_sessions", ["public_id"], unique=True)
    op.create_unique_constraint(
        "uq_parking_sessions_qr_token_hash", "parking_sessions", ["qr_token_hash"]
    )
    op.create_index("ix_parking_sessions_parking_lot_id", "parking_sessions", ["parking_lot_id"])
    op.create_index("ix_parking_sessions_parking_slot_id", "parking_sessions", ["parking_slot_id"])
    op.create_index("ix_parking_sessions_vehicle_id", "parking_sessions", ["vehicle_id"])
    op.create_index("ix_parking_sessions_customer_id", "parking_sessions", ["customer_id"])
    op.create_index("ix_parking_sessions_status", "parking_sessions", ["status"])
    op.create_index("ix_parking_sessions_vehicle_status", "parking_sessions", ["vehicle_id", "status"])
    op.create_index(
        "uq_parking_sessions_active_slot",
        "parking_sessions",
        ["parking_slot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND parking_slot_id IS NOT NULL"),
    )
    op.create_index(
        "uq_parking_sessions_active_vehicle",
        "parking_sessions",
        ["vehicle_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "incidents",
        sa.Column("parking_lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parking_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parking_lot_id"], ["parking_lots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parking_session_id"], ["parking_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_parking_lot_id", "incidents", ["parking_lot_id"])
    op.create_index("ix_incidents_reporter_id", "incidents", ["reporter_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])


def downgrade() -> None:
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_reporter_id", table_name="incidents")
    op.drop_index("ix_incidents_parking_lot_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_corporate_passes_status", table_name="corporate_passes")
    op.drop_index("ix_corporate_passes_pass_type", table_name="corporate_passes")
    op.drop_index("ix_corporate_passes_holder_user_id", table_name="corporate_passes")
    op.drop_index("ix_corporate_passes_parking_lot_id", table_name="corporate_passes")
    op.drop_index("ix_corporate_passes_pass_code", table_name="corporate_passes")
    op.drop_index("ix_bookings_corporate_pass_id", table_name="bookings")
    op.drop_constraint("fk_bookings_corporate_pass_id", "bookings", type_="foreignkey")
    op.drop_column("bookings", "corporate_pass_id")
    op.drop_table("corporate_passes")
    op.drop_index("uq_parking_sessions_active_slot", table_name="parking_sessions")
    op.drop_index("uq_parking_sessions_active_vehicle", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_vehicle_status", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_status", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_customer_id", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_vehicle_id", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_parking_slot_id", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_parking_lot_id", table_name="parking_sessions")
    op.drop_constraint(
        "uq_parking_sessions_qr_token_hash", "parking_sessions", type_="unique"
    )
    op.drop_index("ix_parking_sessions_public_id", table_name="parking_sessions")
    op.drop_table("parking_sessions")
    op.drop_index("uq_staff_lot_assignment", table_name="staff_assignments")
    op.drop_index("ix_staff_assignments_parking_lot_id", table_name="staff_assignments")
    op.drop_index("ix_staff_assignments_staff_user_id", table_name="staff_assignments")
    op.drop_table("staff_assignments")
    op.drop_index("uq_vehicles_normalized_plate", table_name="vehicles")
    op.drop_index("ix_vehicles_user_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_otp_challenges_phone_created", table_name="otp_challenges")
    op.drop_table("otp_challenges")
    op.drop_index("ix_parking_slots_zone_id", table_name="parking_slots")
    op.drop_index("ix_parking_slots_level_id", table_name="parking_slots")
    op.drop_constraint("fk_parking_slots_zone_id", "parking_slots", type_="foreignkey")
    op.drop_constraint("fk_parking_slots_level_id", "parking_slots", type_="foreignkey")
    op.drop_column("parking_slots", "zone_id")
    op.drop_column("parking_slots", "level_id")
    op.drop_column("parking_slots", "zone_name")
    op.drop_column("parking_slots", "level_name")
    op.drop_column("parking_slots", "category")
    op.drop_column("parking_lots", "closure_message")
    op.drop_column("parking_lots", "is_closed")
    op.drop_column("parking_lots", "identification_method")
    op.drop_column("parking_lots", "parking_mode")
    op.drop_column("parking_lots", "parking_type")
    op.drop_index("ix_parking_zones_parking_level_id", table_name="parking_zones")
    op.drop_table("parking_zones")
    op.drop_index("ix_parking_levels_parking_lot_id", table_name="parking_levels")
    op.drop_table("parking_levels")
    op.drop_index("ix_users_phone", table_name="users")
