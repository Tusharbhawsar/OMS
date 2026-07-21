"""Make all datetime columns naive (timestamp WITHOUT time zone).

The whole application works in naive IST: ist_now() and every uploaded outage
time are naive IST datetimes that are compared directly. The original schema used
DateTime(timezone=True) (Postgres timestamptz). On a UTC server psycopg interpreted
the naive IST values we write as UTC, and on read ensure_ist() converted them back
UTC->IST, shifting every time +5:30. That made the "Next Scheduled Outage" countdown
wrong by ~5h30m on Lightsail (UTC) while looking fine on a local IST box.

Switching the columns to naive timestamp makes the values round-trip unchanged on
any server/session timezone, so naive IST stays naive IST everywhere.

Revision ID: 0002_naive_datetime_columns
Revises: 0001_initial_schema
Create Date: 2026-06-19 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_naive_datetime_columns"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


# table -> [datetime columns to convert]
DATETIME_COLUMNS = {
    "customer": ["created_at"],
    "customer_service_point": ["linked_at"],
    "outage_event": ["start_time", "estimated_end_time", "actual_end_time", "created_at"],
    "outage_circuit_map": ["linked_at"],
    "raw_outage_event": ["received_at"],
    "notification": ["sent_at", "delivered_at"],
    "notification_attempt": ["attempted_at"],
}


def upgrade() -> None:
    bind = op.get_bind()
    # On Postgres a plain TYPE change from timestamptz to timestamp converts existing
    # values using the session timezone. We pin the conversion to IST so any genuinely
    # correct instant is read back as the IST wall-clock the app expects. (For this 
    # the data is re-uploaded after migrating, so existing-row conversion is moot.)
    is_postgres = bind.dialect.name == "postgresql"
    for table, columns in DATETIME_COLUMNS.items():
        for column in columns:
            kwargs = {
                "existing_type": sa.DateTime(timezone=True),
                "type_": sa.DateTime(timezone=False),
            }
            if is_postgres:
                kwargs["postgresql_using"] = f"{column} AT TIME ZONE 'Asia/Kolkata'"
            op.alter_column(table, column, **kwargs)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    for table, columns in DATETIME_COLUMNS.items():
        for column in columns:
            kwargs = {
                "existing_type": sa.DateTime(timezone=False),
                "type_": sa.DateTime(timezone=True),
            }
            if is_postgres:
                kwargs["postgresql_using"] = f"{column} AT TIME ZONE 'Asia/Kolkata'"
            op.alter_column(table, column, **kwargs)
