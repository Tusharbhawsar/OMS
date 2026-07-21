"""Guard for the naive-IST datetime invariant.

The app stores and compares every datetime as naive IST (see app.utils.time).
If any column is declared DateTime(timezone=True) again, Postgres timestamptz
behavior reintroduces the UTC<->IST +5:30 shift that broke the "Next Scheduled
Outage" countdown on the UTC Lightsail box. These tests fail loudly if that
invariant is ever reverted.
"""
from datetime import datetime

from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.outage import OutageEvent

# Import the model modules so every table is registered on Base.metadata.
import app.models.customer  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.outage  # noqa: F401
import app.models.reference  # noqa: F401


def test_all_datetime_columns_are_naive() -> None:
    """No mapped column may use a timezone-aware DateTime."""
    aware_columns = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime) and column.type.timezone
    ]
    assert aware_columns == [], (
        "These columns are timezone-aware; they must be naive DateTime to keep the "
        f"naive-IST invariant: {aware_columns}"
    )


def test_outage_start_time_round_trips_unchanged() -> None:
    """A naive value written to start_time comes back byte-for-byte equal and naive."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    start = datetime(2026, 6, 19, 11, 31, 0)  # naive IST wall clock
    with Session(engine) as db:
        db.add(OutageEvent(outage_id="OTG_TZ_001", outage_type="Planned", status="Scheduled", start_time=start))
        db.commit()

    with Session(engine) as db:
        stored = db.scalar(select(OutageEvent.start_time).where(OutageEvent.outage_id == "OTG_TZ_001"))
        assert stored == start
        assert stored.tzinfo is None
