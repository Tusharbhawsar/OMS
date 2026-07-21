from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.customer import CustomerServicePoint, ServicePoint
from app.models.notification import Notification
from app.models.outage import OutageCircuitMap, OutageCustomerMap, OutageEvent
from app.repositories.base import BaseRepository
from app.utils.time import ensure_ist, ist_now


class DashboardRepository(BaseRepository[OutageEvent]):
    """Read-optimized dashboard queries for Phase 1."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self) -> dict[str, object]:
        # "Active" now means the outage is genuinely in progress (power is out).
        active_outages = int(
            self.db.scalar(select(func.count()).select_from(OutageEvent).where(OutageEvent.status == "Active")) or 0
        )
        # "Scheduled / Pending" outages are planned for the future; power is still on.
        scheduled_pending = int(
            self.db.scalar(select(func.count()).select_from(OutageEvent).where(OutageEvent.status == "Scheduled")) or 0
        )
        # Cancelled outages: explicit Cancelled status or the cancellation flag set by the source feed.
        cancelled_outages = int(
            self.db.scalar(
                select(func.count())
                .select_from(OutageEvent)
                .where((OutageEvent.status == "Cancelled") | (OutageEvent.cancellation_flag.is_(True)))
            )
            or 0
        )
        # Completed outages: work finished and power restored.
        completed_outages = int(
            self.db.scalar(
                select(func.count()).select_from(OutageEvent).where(OutageEvent.status.in_(["Completed", "Restored", "Resolved"]))
            )
            or 0
        )
        total_outages = int(self.db.scalar(select(func.count()).select_from(OutageEvent)) or 0)
        # Next upcoming planned outage that has not started yet (earliest future Scheduled start).
        now = ist_now()
        next_scheduled = self.db.execute(
            select(OutageEvent.outage_id, OutageEvent.start_time)
            .where(OutageEvent.status == "Scheduled")
            .where(OutageEvent.start_time.is_not(None))
            .where(OutageEvent.start_time > now)
            .order_by(OutageEvent.start_time.asc())
            .limit(1)
        ).first()
        # Time columns are now naive DateTime (timestamp without time zone), so Postgres and
        # SQLite both return naive IST values that round-trip unchanged regardless of the
        # server/session timezone. ensure_ist() is kept as a defensive normalizer: if any
        # aware value ever reaches here it is converted to naive IST so all datetime math
        # stays naive and never raises aware-vs-naive TypeErrors.
        next_scheduled_start_dt = ensure_ist(next_scheduled.start_time) if next_scheduled else None
        next_scheduled_outage_id = next_scheduled.outage_id if next_scheduled else None
        next_scheduled_start = next_scheduled_start_dt.isoformat() if next_scheduled_start_dt else None
        seconds_until_next_scheduled = (
            int((next_scheduled_start_dt - now).total_seconds()) if next_scheduled_start_dt else None
        )
        # affected_customers = int(self.db.scalar(select(func.count()).select_from(OutageCustomerMap)) or 0) #return total of affected customer from different outages means one cust can be affected by the multiple outages
        affected_customers = int(
            self.db.scalar(
                select(func.count(func.distinct(OutageCustomerMap.customer_id)))
                .join(OutageEvent, OutageEvent.outage_id == OutageCustomerMap.outage_id)
                # .where(OutageEvent.status.in_(["Active", "Scheduled"]))
                .where(OutageEvent.status.in_(["Active"]))
            )
            or 0
        )
        notifications_sent = int(self.db.scalar(select(func.count()).select_from(Notification)) or 0)
        notifications_delivered = int(
            self.db.scalar(select(func.count()).select_from(Notification).where(Notification.status == "Delivered")) or 0
        )
        notifications_failed = int(
            self.db.scalar(select(func.count()).select_from(Notification).where(Notification.status == "Failed")) or 0
        )
        medical_baseline_pending = int(
            self.db.scalar(
                select(func.count())
                .select_from(OutageCustomerMap)
                .join(OutageEvent, OutageEvent.outage_id == OutageCustomerMap.outage_id)
                .join(CustomerServicePoint, CustomerServicePoint.customer_id == OutageCustomerMap.customer_id)
                .where(OutageEvent.status.in_(["Active","Scheduled"]))
                # .where(OutageEvent.status == "Active"
                .where(CustomerServicePoint.is_medical_baseline.is_(True))
                .where(OutageCustomerMap.notification_flag.is_(False))
            )
            or 0
        )
        # breakpoint()
        return {
            "active_outages": active_outages,
            "scheduled_pending": scheduled_pending,
            "cancelled_outages": cancelled_outages,
            "completed_outages": completed_outages,
            "next_scheduled_outage_id": next_scheduled_outage_id,
            "next_scheduled_start": next_scheduled_start,
            "seconds_until_next_scheduled": seconds_until_next_scheduled,
            "total_outages": total_outages,
            "affected_customers": affected_customers,
            "medical_baseline_pending": medical_baseline_pending,
            "notifications_sent": notifications_sent,
            "notifications_delivered": notifications_delivered,
            "notifications_failed": notifications_failed,
        }
    

# Active planned outages on the dashboard 
    def active_outage_rows(self) -> list[dict[str, object]]:
        stmt = (
            select(
                OutageEvent.outage_id,
                OutageEvent.outage_type,
                OutageEvent.status,
                func.min(ServicePoint.geographic_region).label("region"),
                func.count(func.distinct(OutageCustomerMap.customer_id)).label("affected_customers"),
                func.count(
                    func.distinct(case((CustomerServicePoint.is_medical_baseline.is_(True), OutageCustomerMap.customer_id)))
                ).label("medical_baseline_customers"),
                func.count(func.distinct(Notification.notification_id)).label("notifications_sent"),
                OutageEvent.start_time,
                OutageEvent.estimated_end_time,
            )
            .select_from(OutageEvent)
            .outerjoin(OutageCircuitMap, OutageCircuitMap.outage_id == OutageEvent.outage_id)
            .outerjoin(
                ServicePoint,
                (ServicePoint.circuit_id == OutageCircuitMap.circuit_id)
                & (ServicePoint.transformer_id == OutageCircuitMap.transformer_id),
            )
            .outerjoin(OutageCustomerMap, OutageCustomerMap.outage_id == OutageEvent.outage_id)
            .outerjoin(CustomerServicePoint, CustomerServicePoint.customer_id == OutageCustomerMap.customer_id)
            .outerjoin(Notification, Notification.outage_id == OutageEvent.outage_id)
            .where(OutageEvent.status.in_(["Active"]))
            # .where(OutageEvent.status.in_(["Active","Scheduled"]))
            .where(OutageEvent.outage_type == "Planned")
            .group_by(OutageEvent.outage_id, OutageEvent.outage_type, OutageEvent.status, OutageEvent.start_time, OutageEvent.estimated_end_time)
            .order_by(OutageEvent.start_time.asc())
        )
        result = self.db.execute(stmt).mappings().all()
        # breakpoint()
        # return [dict(row) for row in self.db.execute(stmt).mappings().all()]
        return [dict(row) for row in result]
    
