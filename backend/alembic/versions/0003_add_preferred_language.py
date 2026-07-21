"""Add preferred_language to customer for multilingual notifications.

Drives the language of LLM-generated notification messages (e.g. "en", "es").
Added with a NOT NULL "en" default so existing customer rows stay valid.

Revision ID: 0003_add_preferred_language
Revises: 0002_naive_datetime_columns
Create Date: 2026-06-26 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_add_preferred_language"
down_revision = "0002_naive_datetime_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer",
        sa.Column("preferred_language", sa.String(length=10), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    op.drop_column("customer", "preferred_language")
