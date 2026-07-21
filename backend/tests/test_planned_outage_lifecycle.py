from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.customer import Customer  # noqa: F401 - registers table metadata
from app.models.notification import Notification
from app.models.outage import OutageEvent
from app.models.reference import ChannelMaster  # noqa: F401 - registers table metadata
from app.services.planned_outage_service import PlannedOutageService
from app.utils.time import IST


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def add_outage(
    db: Session,
    outage_id: str,
    *,
    status: str = "Scheduled",
    start_time: datetime,
    estimated_end_time: datetime | None = None,
    actual_end_time: datetime | None = None,
    cancellation_flag: bool = False,
) -> None:
    db.add(
        OutageEvent(
            outage_id=outage_id,
            outage_type="Planned",
            status=status,
            start_time=start_time,
            estimated_end_time=estimated_end_time or start_time + timedelta(hours=1),
            actual_end_time=actual_end_time,
            etr_predicted_by_ml=False,
            cancellation_flag=cancellation_flag,
        )
    )
    db.flush()


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


def as_uploaded_ist(value: datetime) -> datetime:
    return value.astimezone(IST).replace(tzinfo=None)


def notification_types_due(db: Session, now: datetime) -> list[str]:
    return [notification_type for _, notification_type in PlannedOutageService(db).get_due_lifecycle_notifications(now)]


# def test_scheduler_selects_advance_notice_for_scheduled_outage_inside_three_minute_window() -> None:
#     now = datetime(2026, 5, 25, 15, 0, tzinfo=timezone.utc)
#     with make_session() as db:
#         add_outage(db, "OTG00001", start_time=as_uploaded_ist(now + timedelta(seconds=120)))

#         assert notification_types_due(db, now) == ["Advance Notice"]


# def test_scheduler_selects_reminder_only_after_advance_notice_has_aged() -> None:
#     now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc) # 3:00
#     # now = datetime(2026, 5, 20, 10, 0) # 3:00

#     with make_session() as db:
#         add_outage(db, "OTG00002", start_time=as_uploaded_ist(now + timedelta(seconds=45)))
#         # add_outage(db, "OTG00002", start_time=now + timedelta(seconds=45)) #3:45
#         add_notification(db, "OTG00002", "Advance Notice", now - timedelta(minutes=31))

#         # breakpoint()
#         assert notification_types_due(db, now) == ["Reminder"]


# def test_scheduler_sends_advance_before_reminder_when_no_advance_exists() -> None:
#     now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
#     with make_session() as db:
#         add_outage(db, "OTG00003", start_time=as_uploaded_ist(now + timedelta(seconds=120)))

#         assert notification_types_due(db, now) == ["Advance Notice"]


# def test_scheduler_selects_outage_start_when_start_time_is_reached() -> None:
#     now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
#     with make_session() as db:
#         add_outage(db, "OTG00004", status="Active", start_time=as_uploaded_ist(now - timedelta(minutes=1)))

#         assert notification_types_due(db, now) == ["Outage Start"]


def test_scheduler_selects_restored_only_when_restoration_is_confirmed() -> None:
    now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
    with make_session() as db:
        add_outage(
            db,
            "OTG00005",
            status="Restored",
            start_time=as_uploaded_ist(now - timedelta(hours=2)),
            actual_end_time=as_uploaded_ist(now - timedelta(minutes=5)),
        )

        assert notification_types_due(db, now) == ["Outage Restored"]


# def test_scheduler_selects_cancellation_alert_before_other_lifecycle_messages() -> None:
#     now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
#     with make_session() as db:
#         add_outage(db, "OTG00006", start_time=as_uploaded_ist(now - timedelta(minutes=1)), cancellation_flag=True)

#         assert notification_types_due(db, now) == ["Cancellation Alert"]


# def test_scheduler_stops_lifecycle_after_cancellation_alert() -> None:
#     now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
#     with make_session() as db:
#         add_outage(db, "OTG00008", start_time=as_uploaded_ist(now - timedelta(minutes=1)), cancellation_flag=True)
#         add_notification(db, "OTG00008", "Cancellation Alert", now - timedelta(minutes=2))

#         assert notification_types_due(db, now) == []


# def test_scheduler_does_not_repeat_an_already_sent_stage() -> None:
#     now = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
#     with make_session() as db:
#         add_outage(db, "OTG00007", status="Active", start_time=as_uploaded_ist(now - timedelta(minutes=1)))
#         add_notification(db, "OTG00007", "Outage Start", now - timedelta(minutes=1))

#         assert notification_types_due(db, now) == []
