"""fix synthetic email domain for phone-created accounts

Revision ID: 4f3c2d91a6b8
Revises: ce17e981b4a2
Create Date: 2026-10-03
"""

from typing import Sequence

from alembic import op

revision: str = "4f3c2d91a6b8"
down_revision: str | None = "ce17e981b4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE users "
        "SET email = replace(email, '@phone.parken.local', '@users.example.com') "
        "WHERE email ~ '^[0-9a-f]{16}@phone\\.parken\\.local$'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users "
        "SET email = replace(email, '@users.example.com', '@phone.parken.local') "
        "WHERE email ~ '^[0-9a-f]{16}@users\\.example\\.com$'"
    )
