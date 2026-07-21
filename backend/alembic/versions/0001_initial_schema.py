"""Initial normalized outage schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-09 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_type",
        sa.Column("customer_type_id", sa.String(length=50), primary_key=True),
        sa.Column("type_name", sa.String(length=50), nullable=False, unique=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="99"),
        sa.Column("description", sa.String(length=200), nullable=True),
    )
    op.create_table(
        "channel_master",
        sa.Column("channel_id", sa.String(length=50), primary_key=True),
        sa.Column("channel_name", sa.String(length=50), nullable=False, unique=True),
        sa.Column("description", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "customer",
        sa.Column("customer_id", sa.String(length=50), primary_key=True),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_customer_account_number", "customer", ["account_number"])
    op.create_table(
        "service_point",
        sa.Column("service_point_id", sa.String(length=50), primary_key=True),
        sa.Column("circuit_id", sa.String(length=50), nullable=False),
        sa.Column("transformer_id", sa.String(length=50), nullable=False),
        sa.Column("geographic_region", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
    )
    op.create_index("ix_service_point_circuit_id", "service_point", ["circuit_id"])
    op.create_index("ix_service_point_transformer_id", "service_point", ["transformer_id"])
    op.create_index("ix_service_point_geographic_region", "service_point", ["geographic_region"])
    op.create_table(
        "outage_event",
        sa.Column("outage_id", sa.String(length=50), primary_key=True),
        sa.Column("outage_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("etr_predicted_by_ml", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cancellation_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outage_event_outage_type", "outage_event", ["outage_type"])
    op.create_index("ix_outage_event_status", "outage_event", ["status"])
    op.create_index("ix_outage_event_start_time", "outage_event", ["start_time"])
    op.create_table(
        "customer_service_point",
        sa.Column("customer_id", sa.String(length=50), sa.ForeignKey("customer.customer_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("service_point_id", sa.String(length=50), sa.ForeignKey("service_point.service_point_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("customer_type_id", sa.String(length=50), sa.ForeignKey("customer_type.customer_type_id"), nullable=False),
        sa.Column("channel_id", sa.String(length=50), sa.ForeignKey("channel_master.channel_id"), nullable=False),
        sa.Column("is_medical_baseline", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "outage_circuit_map",
        sa.Column("outage_id", sa.String(length=50), sa.ForeignKey("outage_event.outage_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("circuit_id", sa.String(length=50), primary_key=True),
        sa.Column("transformer_id", sa.String(length=50), primary_key=True),
        sa.Column("affected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "outage_customer_map",
        sa.Column("outage_id", sa.String(length=50), sa.ForeignKey("outage_event.outage_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("customer_id", sa.String(length=50), sa.ForeignKey("customer.customer_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("notification_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("restored_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "notification",
        sa.Column("notification_id", sa.String(length=50), primary_key=True),
        sa.Column("outage_id", sa.String(length=50), sa.ForeignKey("outage_event.outage_id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.String(length=50), sa.ForeignKey("customer.customer_id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("channel_id", sa.String(length=50), sa.ForeignKey("channel_master.channel_id"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_content", sa.Text(), nullable=False),
    )
    op.create_index("ix_notification_outage_id", "notification", ["outage_id"])
    op.create_index("ix_notification_customer_id", "notification", ["customer_id"])
    op.create_index("ix_notification_notification_type", "notification", ["notification_type"])
    op.create_index("ix_notification_status", "notification", ["status"])
    op.create_table(
        "notification_attempt",
        sa.Column("attempt_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("notification_id", sa.String(length=50), sa.ForeignKey("notification.notification_id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("provider_message_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notification_attempt_notification_id", "notification_attempt", ["notification_id"])
    op.create_table(
        "raw_outage_event",
        sa.Column("raw_event_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("external_event_id", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_raw_outage_event_external_event_id", "raw_outage_event", ["external_event_id"])


def downgrade() -> None:
    op.drop_index("ix_raw_outage_event_external_event_id", table_name="raw_outage_event")
    op.drop_table("raw_outage_event")
    op.drop_index("ix_notification_attempt_notification_id", table_name="notification_attempt")
    op.drop_table("notification_attempt")
    op.drop_index("ix_notification_status", table_name="notification")
    op.drop_index("ix_notification_notification_type", table_name="notification")
    op.drop_index("ix_notification_customer_id", table_name="notification")
    op.drop_index("ix_notification_outage_id", table_name="notification")
    op.drop_table("notification")
    op.drop_table("outage_customer_map")
    op.drop_table("outage_circuit_map")
    op.drop_table("customer_service_point")
    op.drop_index("ix_outage_event_start_time", table_name="outage_event")
    op.drop_index("ix_outage_event_status", table_name="outage_event")
    op.drop_index("ix_outage_event_outage_type", table_name="outage_event")
    op.drop_table("outage_event")
    op.drop_index("ix_service_point_geographic_region", table_name="service_point")
    op.drop_index("ix_service_point_transformer_id", table_name="service_point")
    op.drop_index("ix_service_point_circuit_id", table_name="service_point")
    op.drop_table("service_point")
    op.drop_index("ix_customer_account_number", table_name="customer")
    op.drop_table("customer")
    op.drop_table("channel_master")
    op.drop_table("customer_type")
