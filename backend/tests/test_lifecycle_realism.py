"""Tests for real-world lifecycle realism (Option 2 import guards + Option 3 cancel event)."""
from datetime import datetime
from io import BytesIO

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.endpoints.outages import cancel_outage, restore_outage
from app.core.database import Base
from app.core.exceptions import AppException
from app.models.outage import OutageEvent
from app.services.file_ingestion_service import FileIngestionService


def make_db() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def _outage_workbook(rows: list[dict]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="OUTAGE_EVENT", index=False)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Option 2 — import strips "future knowledge" from live outages
# --------------------------------------------------------------------------- #
def test_option2_scheduled_outage_strips_actual_end_and_cancellation() -> None:
    with make_db() as db:
        FileIngestionService(db).import_upload(
            "d.xlsx",
            _outage_workbook([{
                "outage_id": "OTG1", "outage_type": "Planned", "status": "Scheduled",
                "start_time": "2026-06-19 15:00", "estimated_end_time": "2026-06-19 16:00",
                "actual_end_time": "2026-06-19 16:05", "cancellation_flag": True,
            }]),
        )
        outage = db.get(OutageEvent, "OTG1")
        assert outage.actual_end_time is None          # cannot have ended yet
        assert outage.cancellation_flag is False        # cancellation must come as an event


def test_option2_historical_completed_outage_is_preserved() -> None:
    with make_db() as db:
        FileIngestionService(db).import_upload(
            "d.xlsx",
            _outage_workbook([{
                "outage_id": "OTG2", "outage_type": "Planned", "status": "Completed",
                "start_time": "2026-06-18 15:00", "estimated_end_time": "2026-06-18 16:00",
                "actual_end_time": "2026-06-18 16:05",
            }]),
        )
        outage = db.get(OutageEvent, "OTG2")
        assert outage.actual_end_time == datetime(2026, 6, 18, 16, 5)   # real history untouched


# --------------------------------------------------------------------------- #
# Option 3 — cancellation as an event
# --------------------------------------------------------------------------- #
def test_option3_cancel_sets_flag_status_and_timestamp() -> None:
    with make_db() as db:
        db.add(OutageEvent(outage_id="OTG3", outage_type="Planned", status="Scheduled"))
        db.commit()

        resp = cancel_outage("OTG3", db)

        assert resp["data"]["cancellation_flag"] is True
        assert resp["data"]["status"] == "Cancelled"
        assert resp["data"]["cancelled_at"] is not None
        stored = db.get(OutageEvent, "OTG3")
        assert stored.cancellation_flag is True and stored.cancelled_at is not None


def test_option3_cancel_is_idempotent() -> None:
    with make_db() as db:
        db.add(OutageEvent(outage_id="OTG4", outage_type="Planned", status="Scheduled"))
        db.commit()
        cancel_outage("OTG4", db)
        resp = cancel_outage("OTG4", db)
        assert resp["message"] == "Outage already cancelled"


def test_option3_cannot_cancel_finished_outage() -> None:
    with make_db() as db:
        db.add(OutageEvent(outage_id="OTG5", outage_type="Planned", status="Completed"))
        db.commit()
        with pytest.raises(AppException):
            cancel_outage("OTG5", db)


def test_option3_cancel_missing_outage_raises() -> None:
    with make_db() as db:
        with pytest.raises(AppException):
            cancel_outage("NOPE", db)


# --------------------------------------------------------------------------- #
# Option 3 — restoration as an event (counterpart to cancel)
# --------------------------------------------------------------------------- #
def test_option3_restore_sets_actual_end_and_status() -> None:
    with make_db() as db:
        db.add(OutageEvent(outage_id="OTG6", outage_type="Planned", status="Active"))
        db.commit()

        resp = restore_outage("OTG6", db)

        assert resp["data"]["status"] == "Restored"
        assert resp["data"]["actual_end_time"] is not None
        stored = db.get(OutageEvent, "OTG6")
        assert stored.actual_end_time is not None


def test_option3_restored_outage_stays_a_lifecycle_candidate_and_is_due() -> None:
    """Regression: status must keep the outage in the batch's candidate set so the
    "Outage Restored" notification actually fires (Completed was silently excluded)."""
    from datetime import timedelta

    from app.repositories.outage_repository import OutageRepository
    from app.services.planned_outage_service import PlannedOutageService
    from app.utils.time import ist_now

    with make_db() as db:
        db.add(OutageEvent(
            outage_id="OTG_R", outage_type="Planned", status="Active",
            start_time=ist_now() - timedelta(minutes=10),
        ))
        db.commit()
        restore_outage("OTG_R", db)

        candidates = OutageRepository(db).list_planned_lifecycle_candidates()
        assert any(o.outage_id == "OTG_R" for o in candidates)

        outage = db.get(OutageEvent, "OTG_R")
        due = PlannedOutageService(db)._next_due_notification_type(outage, ist_now())
        assert due == "Outage Restored"


def test_option3_restore_is_idempotent() -> None:
    with make_db() as db:
        db.add(OutageEvent(outage_id="OTG7", outage_type="Planned", status="Active"))
        db.commit()
        restore_outage("OTG7", db)
        resp = restore_outage("OTG7", db)
        assert resp["message"] == "Outage already restored"


def test_option3_cannot_restore_cancelled_outage() -> None:
    with make_db() as db:
        db.add(OutageEvent(outage_id="OTG8", outage_type="Planned", status="Cancelled", cancellation_flag=True))
        db.commit()
        with pytest.raises(AppException):
            restore_outage("OTG8", db)


def test_option3_restore_missing_outage_raises() -> None:
    with make_db() as db:
        with pytest.raises(AppException):
            restore_outage("NOPE", db)
