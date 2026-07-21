"""Automated coverage for the MLEU (Planned Outage Communication) test scenarios.

Each test name carries the matching TC ID from MLEU_Test_Scenarios.xlsx so the
workbook's Actual Result / Status columns can be filled from this run.

The suite exercises the deterministic business logic end to end without any
external services: file ingestion (in-memory workbooks), outage validation,
affected-customer identification (Medical Baseline priority), notification
dispatch (sandbox), lifecycle timing windows, status transitions, the batch
job, and the API response envelopes.
"""
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.exceptions import AppException
from app.main import app
from app.models.customer import Customer, CustomerServicePoint, ServicePoint
from app.models.notification import Notification
from app.models.outage import OutageCircuitMap, OutageCustomerMap, OutageEvent
from app.models.reference import ChannelMaster, CustomerType
from app.repositories.notification_repository import NotificationRepository
from app.services.customer_mapping_service import CustomerMappingService
from app.services.file_ingestion_service import FileIngestionService
from app.services.notification_service import NotificationService, get_destination_for_channel
from app.services.planned_outage_service import PlannedOutageService
from app.utils.time import IST, ist_now

NOW = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def as_uploaded_ist(value: datetime) -> datetime:
    """Mimic how uploaded timestamps are stored (IST, tz-naive)."""
    return value.astimezone(IST).replace(tzinfo=None)


def real_now_naive_ist() -> datetime:
    """process_due_outages() uses the real clock, so anchor batch tests to it."""
    now = ist_now()
    return now.replace(tzinfo=None) if now.tzinfo else now


def add_outage(
    db: Session,
    outage_id: str,
    *,
    outage_type: str = "Planned",
    status: str = "Scheduled",
    start_time: datetime,
    estimated_end_time: datetime | None = None,
    actual_end_time: datetime | None = None,
    cancellation_flag: bool = False,
) -> OutageEvent:
    outage = OutageEvent(
        outage_id=outage_id,
        outage_type=outage_type,
        status=status,
        start_time=start_time,
        estimated_end_time=estimated_end_time or start_time + timedelta(hours=1),
        actual_end_time=actual_end_time,
        etr_predicted_by_ml=False,
        cancellation_flag=cancellation_flag,
    )
    db.add(outage)
    db.flush()
    return outage


def add_notification(db: Session, outage_id: str, notification_type: str, sent_at: datetime) -> None:
    db.add(
        Notification(
            notification_id=f"NTF-{outage_id}-{notification_type.replace(' ', '-')}",
            outage_id=outage_id,
            customer_id="CUST00001",
            notification_type=notification_type,
            channel_id="CH001",
            status="Delivered",
            sent_at=sent_at,
            delivered_at=sent_at,
            message_content="test",
        )
    )
    db.flush()


def types_due(db: Session, now: datetime) -> list[str]:
    return [ntype for _, ntype in PlannedOutageService(db).get_due_lifecycle_notifications(now)]


def seed_customer(
    db: Session,
    *,
    customer_id: str,
    channel_id: str = "CH001",
    channel_name: str = "Email",
    is_medical_baseline: bool = False,
    priority: int = 3,
) -> None:
    """Seed a fully-mapped customer reachable through circuit mapping (CKT1/TRF1)."""
    if db.get(ChannelMaster, channel_id) is None:
        db.add(ChannelMaster(channel_id=channel_id, channel_name=channel_name, is_active=True))
    type_id = f"CT{priority:03d}"
    if db.get(CustomerType, type_id) is None:
        db.add(CustomerType(customer_type_id=type_id, type_name=f"Type{priority}", priority=priority))
    db.add(Customer(customer_id=customer_id, account_number=f"ACC-{customer_id}",
                    first_name="Test", last_name=customer_id,
                    email="user@example.com", phone="+15551234567", is_active=True))
    sp_id = f"SP-{customer_id}"
    db.add(ServicePoint(service_point_id=sp_id, circuit_id="CKT1", transformer_id="TRF1"))
    db.add(CustomerServicePoint(customer_id=customer_id, service_point_id=sp_id,
                                customer_type_id=type_id, channel_id=channel_id,
                                is_medical_baseline=is_medical_baseline))
    db.flush()


def _customer_dict(channel_name: str, channel_id: str, **over) -> dict:
    base = {
        "customer_id": "CUST00001", "first_name": "Test", "last_name": "User",
        "channel_name": channel_name, "channel_id": channel_id,
        "email": "user@example.com", "phone": "+15551234567",
    }
    base.update(over)
    return base


def build_workbook(*, include_customer_map: bool = True) -> bytes:
    """Build a minimal but valid workbook in memory."""
    sheets = {
        "CUSTOMER_TYPE": pd.DataFrame([{"customer_type_id": "CT003", "type_name": "Residential", "priority": 3}]),
        "CHANNEL_MASTER": pd.DataFrame([{"channel_id": "CH001", "channel_name": "Email", "is_active": True}]),
        "CUSTOMER": pd.DataFrame([{"customer_id": "CUST00001", "account_number": "ACC1",
                                   "first_name": "Jane", "last_name": "Doe", "is_active": True}]),
        "OUTAGE_EVENT": pd.DataFrame([{"outage_id": "OTG00001", "outage_type": "Planned", "status": "Scheduled",
                                       "start_time": "2026-05-20 15:00", "estimated_end_time": "2026-05-20 16:00"}]),
    }
    if include_customer_map:
        sheets["OUTAGE_CUSTOMER_MAP"] = pd.DataFrame(
            [{"outage_id": "OTG00001", "customer_id": "CUST00001", "notification_flag": True, "restored_flag": False}]
        )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


def build_csv() -> bytes:
    df = pd.DataFrame([{"outage_id": "OTG00050", "outage_type": "Planned", "status": "Scheduled",
                        "start_time": "2026-05-20 15:00", "estimated_end_time": "2026-05-20 16:00"}])
    return df.to_csv(index=False).encode("utf-8")


# --------------------------------------------------------------------------- #
# File Ingestion  (TC001 - TC006)
# --------------------------------------------------------------------------- #
def test_TC001_upload_valid_xlsx_imports_all_sheets() -> None:
    with make_session() as db:
        result = FileIngestionService(db).import_upload("data.xlsx", build_workbook())
        assert result["imported_tables"]["OUTAGE_EVENT"] == 1
        assert result["imported_tables"]["CUSTOMER"] == 1


def test_TC002_upload_valid_csv_imports_outage_events() -> None:
    with make_session() as db:
        result = FileIngestionService(db).import_upload("planned.csv", build_csv())
        assert result["imported_tables"]["OUTAGE_EVENT"] == 1


def test_TC003_missing_sheet_is_skipped_not_fatal() -> None:
    with make_session() as db:
        result = FileIngestionService(db).import_upload("partial.xlsx", build_workbook(include_customer_map=False))
        assert "OUTAGE_CUSTOMER_MAP" in result["skipped_sheets"]   # gracefully skipped
        assert result["imported_tables"]["OUTAGE_EVENT"] == 1       # present sheets still imported


def test_TC004_unsupported_file_type_rejected() -> None:
    with make_session() as db:
        with pytest.raises(AppException) as exc:
            FileIngestionService(db).import_upload("notes.txt", b"hello")
        assert exc.value.error_code == "UNSUPPORTED_FILE_TYPE"


def test_TC005_reupload_is_idempotent() -> None:
    content = build_workbook()
    with make_session() as db:
        FileIngestionService(db).import_upload("data.xlsx", content)
        FileIngestionService(db).import_upload("data.xlsx", content)
        assert db.query(OutageEvent).count() == 1     # upsert, no duplicate
        assert db.query(Customer).count() == 1


def test_TC006_ingestion_status_endpoint_returns_envelope() -> None:
    client = TestClient(app)
    body = client.get("/api/v1/uploads/ingestion-status").json()
    assert body["status_code"] == 200
    assert {"status", "total_records"} <= set(body["data"].keys())


# --------------------------------------------------------------------------- #
# Outage validation  (TC007 - TC010)
# --------------------------------------------------------------------------- #
def test_TC007_process_valid_planned_outage() -> None:
    with make_session() as db:
        add_outage(db, "OTG1", start_time=as_uploaded_ist(NOW - timedelta(minutes=1)))
        result = PlannedOutageService(db).process_outage("OTG1", "Advance Notice")
        assert result["notifications_created"] == 0
        assert result["notification_type"] == "Advance Notice"


def test_TC008_process_unknown_outage_raises_404() -> None:
    with make_session() as db:
        with pytest.raises(AppException) as exc:
            PlannedOutageService(db).process_outage("NOPE", "Advance Notice")
        assert exc.value.status_code == 404
        assert exc.value.error_code == "OUTAGE_NOT_FOUND"


def test_TC009_process_non_planned_outage_rejected() -> None:
    with make_session() as db:
        add_outage(db, "OTG2", outage_type="Unplanned", start_time=as_uploaded_ist(NOW))
        with pytest.raises(AppException) as exc:
            PlannedOutageService(db).process_outage("OTG2", "Advance Notice")
        assert exc.value.error_code == "UNSUPPORTED_OUTAGE_TYPE"


def test_TC010_invalid_notification_type_rejected() -> None:
    with make_session() as db:
        add_outage(db, "OTG3", start_time=as_uploaded_ist(NOW))
        with pytest.raises(AppException) as exc:
            PlannedOutageService(db).process_outage("OTG3", "FooBar")
        assert exc.value.error_code == "INVALID_NOTIFICATION_TYPE"


# --------------------------------------------------------------------------- #
# Customer identification & medical baseline  (TC011 - TC014)
# --------------------------------------------------------------------------- #
def test_TC011_identify_affected_customers() -> None:
    with make_session() as db:
        add_outage(db, "OTG4", start_time=as_uploaded_ist(NOW))
        db.add(OutageCircuitMap(outage_id="OTG4", circuit_id="CKT1", transformer_id="TRF1", affected_count=1))
        seed_customer(db, customer_id="CUST00002")
        customers = CustomerMappingService(db).identify_affected_customers("OTG4")
        assert [c["customer_id"] for c in customers] == ["CUST00002"]


def test_TC012_medical_baseline_customers_prioritised() -> None:
    with make_session() as db:
        add_outage(db, "OTG5", start_time=as_uploaded_ist(NOW))
        db.add(OutageCircuitMap(outage_id="OTG5", circuit_id="CKT1", transformer_id="TRF1", affected_count=2))
        seed_customer(db, customer_id="CUST00001", is_medical_baseline=False)
        seed_customer(db, customer_id="CUST00009", is_medical_baseline=True)
        customers = CustomerMappingService(db).identify_affected_customers("OTG5")
        assert customers[0]["customer_id"] == "CUST00009"
        assert customers[0]["is_medical_baseline"] is True


def test_TC013_outage_with_zero_affected_customers() -> None:
    with make_session() as db:
        add_outage(db, "OTG6", start_time=as_uploaded_ist(NOW))
        assert CustomerMappingService(db).identify_affected_customers("OTG6") == []


def test_TC014_mapping_persistence_is_idempotent() -> None:
    with make_session() as db:
        add_outage(db, "OTG4b", start_time=as_uploaded_ist(NOW))
        db.add(OutageCircuitMap(outage_id="OTG4b", circuit_id="CKT1", transformer_id="TRF1", affected_count=1))
        seed_customer(db, customer_id="CUST00002")
        svc = CustomerMappingService(db)
        svc.identify_affected_customers("OTG4b")
        svc.identify_affected_customers("OTG4b")
        assert db.query(OutageCustomerMap).filter_by(outage_id="OTG4b").count() == 1


# --------------------------------------------------------------------------- #
# Notification dispatch & channels  (TC015 - TC022)
# --------------------------------------------------------------------------- #
def test_TC015_dispatch_email_channel_delivered() -> None:
    with make_session() as db:
        add_outage(db, "OTG7", start_time=as_uploaded_ist(NOW))
        result = NotificationService(db).notify_customers("OTG7", "Advance Notice",
                                                          [_customer_dict("Email", "CH001")])
        assert result == {"created": 1, "delivered": 1, "failed": 0}


def test_TC016_dispatch_sms_channel_delivered() -> None:
    with make_session() as db:
        add_outage(db, "OTG8", start_time=as_uploaded_ist(NOW))
        result = NotificationService(db).notify_customers("OTG8", "Reminder",
                                                          [_customer_dict("SMS", "CH002")])
        assert result == {"created": 1, "delivered": 1, "failed": 0}


def test_TC017_email_destination_falls_back_when_missing() -> None:
    assert get_destination_for_channel("Email", {"email": None}) == "missing-email@example.local"


def test_TC018_sms_destination_falls_back_when_missing() -> None:
    assert get_destination_for_channel("SMS", {"phone": None}) == "+15550000000"


def test_TC019_sandbox_mode_uses_sandbox_provider() -> None:
    # SMS channel always resolves to the sandbox adapter regardless of EMAIL_BACKEND,
    # so it deterministically proves no real provider is contacted in mode.
    with make_session() as db:
        add_outage(db, "OTG_SB", start_time=as_uploaded_ist(NOW))
        NotificationService(db).notify_customers("OTG_SB", "Advance Notice", [_customer_dict("SMS", "CH002")])
        attempt = db.query(Notification).one().attempts[0]
        assert attempt.provider_name == "sandbox_sms"      # no real provider called


def test_TC020_notification_counts_consistent() -> None:
    with make_session() as db:
        add_outage(db, "OTG9", start_time=as_uploaded_ist(NOW))
        customers = [_customer_dict("Email", "CH001", customer_id="CUST00001"),
                     _customer_dict("SMS", "CH002", customer_id="CUST00002")]
        result = NotificationService(db).notify_customers("OTG9", "Outage Start", customers)
        assert result["created"] == 2
        assert result["delivered"] + result["failed"] == 2


def test_TC021_list_notifications_filtered_by_outage() -> None:
    with make_session() as db:
        add_outage(db, "OTGa", start_time=as_uploaded_ist(NOW))
        add_outage(db, "OTGb", start_time=as_uploaded_ist(NOW))
        add_notification(db, "OTGa", "Advance Notice", as_uploaded_ist(NOW))
        add_notification(db, "OTGb", "Advance Notice", as_uploaded_ist(NOW))
        rows = NotificationRepository(db).list_by_outage("OTGa", limit=50)
        assert [n.outage_id for n in rows] == ["OTGa"]


def test_TC022_provider_failure_is_recorded_not_fatal() -> None:
    class _Boom:
        def send(self, payload):  # noqa: ANN001
            raise RuntimeError("provider down")

    with make_session() as db:
        add_outage(db, "OTG10", start_time=as_uploaded_ist(NOW))
        svc = NotificationService(db)
        svc.notifier_factory.get = lambda channel_name: _Boom()  # type: ignore[assignment]
        result = svc.notify_customers("OTG10", "Advance Notice", [_customer_dict("Email", "CH001")])
        assert result == {"created": 1, "delivered": 0, "failed": 1}
        note = db.query(Notification).one()
        assert note.status == "Failed"
        assert note.attempts[0].error_message == "provider down"


# --------------------------------------------------------------------------- #
# Lifecycle scheduling timing  (TC023 - TC033)
# --------------------------------------------------------------------------- #
def test_TC023_advance_notice_selected_in_window() -> None:
    with make_session() as db:
        add_outage(db, "L1", start_time=as_uploaded_ist(NOW + timedelta(seconds=120)))
        assert types_due(db, NOW) == ["Advance Notice"]


def test_TC024_advance_notice_not_selected_outside_window() -> None:
    with make_session() as db:
        add_outage(db, "L2", start_time=as_uploaded_ist(NOW + timedelta(seconds=200)))
        assert types_due(db, NOW) == []


def test_TC025_reminder_selected_after_advance_notice_aged() -> None:
    with make_session() as db:
        add_outage(db, "L3", start_time=as_uploaded_ist(NOW + timedelta(seconds=45)))
        add_notification(db, "L3", "Advance Notice", as_uploaded_ist(NOW - timedelta(minutes=31)))
        assert types_due(db, NOW) == ["Reminder"]


def test_TC026_reminder_suppressed_when_advance_notice_too_recent() -> None:
    with make_session() as db:
        add_outage(db, "L4", start_time=as_uploaded_ist(NOW + timedelta(seconds=45)))
        add_notification(db, "L4", "Advance Notice", as_uploaded_ist(NOW - timedelta(seconds=20)))
        assert types_due(db, NOW) == []


def test_TC027_advance_notice_sent_before_reminder_when_none_exists() -> None:
    with make_session() as db:
        add_outage(db, "L5", start_time=as_uploaded_ist(NOW + timedelta(seconds=120)))
        assert types_due(db, NOW) == ["Advance Notice"]


def test_TC028_outage_start_selected_when_start_reached() -> None:
    with make_session() as db:
        add_outage(db, "L6", status="Active", start_time=as_uploaded_ist(NOW - timedelta(minutes=1)))
        assert types_due(db, NOW) == ["Outage Start"]


def test_TC029_outage_restored_when_confirmed() -> None:
    with make_session() as db:
        add_outage(db, "L7", status="Restored",
                   start_time=as_uploaded_ist(NOW - timedelta(hours=2)),
                   actual_end_time=as_uploaded_ist(NOW - timedelta(minutes=5)))
        assert types_due(db, NOW) == ["Outage Restored"]


def test_TC030_outage_restored_not_sent_before_actual_end() -> None:
    with make_session() as db:
        add_outage(db, "L8", status="Active",
                   start_time=as_uploaded_ist(NOW - timedelta(minutes=5)), actual_end_time=None)
        assert "Outage Restored" not in types_due(db, NOW)


def test_TC031_cancellation_alert_takes_priority() -> None:
    with make_session() as db:
        add_outage(db, "L9", start_time=as_uploaded_ist(NOW - timedelta(minutes=1)), cancellation_flag=True)
        assert types_due(db, NOW) == ["Cancellation Alert"]


def test_TC032_lifecycle_stops_after_cancellation_alert() -> None:
    with make_session() as db:
        add_outage(db, "L10", start_time=as_uploaded_ist(NOW - timedelta(minutes=1)), cancellation_flag=True)
        add_notification(db, "L10", "Cancellation Alert", as_uploaded_ist(NOW - timedelta(minutes=2)))
        assert types_due(db, NOW) == []


def test_TC033_already_sent_stage_not_repeated() -> None:
    with make_session() as db:
        add_outage(db, "L11", status="Active", start_time=as_uploaded_ist(NOW - timedelta(minutes=1)))
        add_notification(db, "L11", "Outage Start", as_uploaded_ist(NOW - timedelta(minutes=1)))
        assert types_due(db, NOW) == []


# --------------------------------------------------------------------------- #
# Status transitions  (TC034 - TC037)
# --------------------------------------------------------------------------- #
def _process_and_status(notification_type: str, *, start_offset_min: int = -1,
                        cancellation: bool = False) -> str:
    with make_session() as db:
        outage = add_outage(db, "S1", status="Scheduled",
                            start_time=as_uploaded_ist(NOW + timedelta(minutes=start_offset_min)),
                            cancellation_flag=cancellation)
        PlannedOutageService(db).process_outage("S1", notification_type)
        db.refresh(outage)
        return outage.status


def test_TC034_outage_start_moves_status_to_active() -> None:
    assert _process_and_status("Outage Start") == "Active"


def test_TC035_outage_restored_moves_status_to_completed() -> None:
    assert _process_and_status("Outage Restored") == "Completed"


def test_TC036_cancellation_alert_moves_status_to_cancelled() -> None:
    assert _process_and_status("Cancellation Alert", cancellation=True) == "Cancelled"


def test_TC037_advance_notice_does_not_change_status() -> None:
    assert _process_and_status("Advance Notice", start_offset_min=5) == "Scheduled"


# --------------------------------------------------------------------------- #
# Batch job  (TC038 - TC040)
# --------------------------------------------------------------------------- #
def test_TC038_batch_processes_due_outages() -> None:
    with make_session() as db:
        add_outage(db, "B1", status="Active", start_time=real_now_naive_ist() - timedelta(minutes=1))
        assert len(PlannedOutageService(db).process_due_outages()) >= 1


def test_TC039_batch_continues_after_single_failure() -> None:
    with make_session() as db:
        add_outage(db, "BAD", status="Active", start_time=real_now_naive_ist() - timedelta(minutes=2))
        add_outage(db, "GOOD", status="Active", start_time=real_now_naive_ist() - timedelta(minutes=1))
        db.commit()   # commit so the batch's per-item rollback does not discard seeded rows
        svc = PlannedOutageService(db)
        original = svc.process_outage

        def flaky(outage_id: str, notification_type: str):
            if outage_id == "BAD":
                raise RuntimeError("boom")
            return original(outage_id, notification_type)

        svc.process_outage = flaky  # type: ignore[assignment]
        results = svc.process_due_outages()
        assert len(results) == 1   # GOOD processed, BAD failure swallowed


def test_TC040_batch_with_no_due_outages_returns_empty() -> None:
    with make_session() as db:
        add_outage(db, "B2", start_time=real_now_naive_ist() + timedelta(days=2))
        assert PlannedOutageService(db).process_due_outages() == []


# --------------------------------------------------------------------------- #
# API / response envelope  (TC041 - TC045)
# --------------------------------------------------------------------------- #
def test_TC041_health_check_returns_200() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status_code"] == 200


def test_TC042_success_response_envelope_shape() -> None:
    body = TestClient(app).get("/api/v1/uploads/ingestion-status").json()
    assert set(body.keys()) >= {"status_code", "message", "data"}


def test_TC043_error_envelope_for_unknown_outage() -> None:
    response = TestClient(app).get("/api/v1/outages/OTG_DOES_NOT_EXIST/affected-customers")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "OUTAGE_NOT_FOUND"
    assert "message" in body


def test_TC044_dashboard_summary_returns_200() -> None:
    response = TestClient(app).get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["status_code"] == 200


def test_TC045_active_outages_returns_200() -> None:
    response = TestClient(app).get("/api/v1/outages/active")
    assert response.status_code == 200
    assert response.json()["status_code"] == 200
