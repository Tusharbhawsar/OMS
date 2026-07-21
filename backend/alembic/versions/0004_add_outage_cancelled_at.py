"""Add outage_event.cancelled_at for event-driven cancellation (Option 3).

Cancellation is a real-world event that arrives after an outage is created, so it gets
its own timestamp (parallel to actual_end_time for restoration). Nullable: null until a
cancellation event flips cancellation_flag/status. Naive DateTime to match the naive-IST
invariant established in 0002.

Revision ID: 0004_add_outage_cancelled_at
Revises: 0003_add_preferred_language
Create Date: 2026-06-23 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_outage_cancelled_at"
down_revision = "0003_add_preferred_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outage_event",
        sa.Column("cancelled_at", sa.DateTime(timezone=False), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outage_event", "cancelled_at")
