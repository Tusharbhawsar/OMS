import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.agents.graph import PlannedOutageAgentGraph
from app.core.exceptions import AppException
from app.models.outage import OutageEvent
from app.repositories.notification_repository import NotificationRepository
from app.repositories.outage_repository import OutageRepository
from app.utils.time import ensure_ist, ist_now

logger = logging.getLogger(__name__)


class PlannedOutageService:
    """Application service for planned outage processing and batch execution."""

    VALID_NOTIFICATION_TYPES = {
        "Advance Notice",
        "Reminder",
        "Outage Start",
        "Outage Restored",
        "Cancellation Alert",
    }

    # When a lifecycle notification is processed, advance the outage status to match
    # the real-world stage so the dashboard reflects Scheduled -> Active -> Completed/Cancelled.
    NOTIFICATION_STATUS_TRANSITIONS = {
        "Outage Start": "Active",
        "Outage Restored": "Completed",
        "Cancellation Alert": "Cancelled",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.outage_repo = OutageRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.agent_graph = PlannedOutageAgentGraph(db)

    def process_outage(self, outage_id: str, notification_type: str) -> dict[str, object]:
        """Process a single planned outage through the LangGraph workflow."""
        if notification_type not in self.VALID_NOTIFICATION_TYPES:
            raise AppException(
                "Invalid notification type",
                400,
                "INVALID_NOTIFICATION_TYPE",
                {"allowed": sorted(self.VALID_NOTIFICATION_TYPES)},
            )

        outage = self.outage_repo.get_by_id(outage_id)
        if outage is None:
            raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})
        if outage.outage_type not in {"Planned"}:
            raise AppException("Only Planned outages are supported in Phase 1", 400, "UNSUPPORTED_OUTAGE_TYPE")

        result = self.agent_graph.run(outage_id=outage_id, notification_type=notification_type)
        self._apply_status_transition(outage, notification_type)
        self.db.commit()
        return result

    def _apply_status_transition(self, outage: OutageEvent, notification_type: str) -> None:
        """Move the outage to its next lifecycle status based on the notification just processed."""
        new_status = self.NOTIFICATION_STATUS_TRANSITIONS.get(notification_type)
        if new_status is not None and outage.status != new_status:
            logger.info(
                "Outage status transition",
                extra={"ctx_outage_id": outage.outage_id, "ctx_from": outage.status, "ctx_to": new_status},
            )
            outage.status = new_status

    def record_actual_end_time(self, outage_id: str, actual_end_time: datetime) -> OutageEvent:
        """Field-person input: record the real on-site restoration time for an outage.

        Storing the actual end time makes the outage due for an "Outage Restored"
        notification on the next lifecycle batch run (see _next_due_notification_type).
        """
        outage = self._get_planned_outage_or_raise(outage_id)

        normalized_end = ensure_ist(actual_end_time)
        start_time = ensure_ist(outage.start_time)
        if start_time is not None and normalized_end is not None and normalized_end < start_time:
            raise AppException(
                "Actual end time cannot be before the outage start time",
                400,
                "INVALID_ACTUAL_END_TIME",
                {"outage_id": outage_id, "start_time": start_time.isoformat()},
            )

        outage.actual_end_time = normalized_end
        logger.info(
            "Actual end time recorded from field",
            extra={"ctx_outage_id": outage_id, "ctx_actual_end_time": normalized_end},
        )
        self.db.commit()
        self.db.refresh(outage)
        return outage

    def set_cancellation_flag(self, outage_id: str, cancel: bool) -> OutageEvent:
        """Operator input: mark a planned outage for cancellation (or revoke it).

        Raising the flag makes the outage due for a "Cancellation Alert" on the
        next lifecycle batch run (see _next_due_notification_type).
        """
        outage = self._get_planned_outage_or_raise(outage_id)
        outage.cancellation_flag = cancel
        logger.info(
            "Cancellation flag updated",
            extra={"ctx_outage_id": outage_id, "ctx_cancellation_flag": cancel},
        )
        self.db.commit()
        self.db.refresh(outage)
        return outage

    def list_outages_in_range(self, range_start: datetime, range_end: datetime | None = None) -> list[OutageEvent]:
        """Return all outages whose start_time falls within the given time range."""
        normalized_start = ensure_ist(range_start)
        normalized_end = ensure_ist(range_end)
        if normalized_start is not None and normalized_end is not None and normalized_end < normalized_start:
            raise AppException(
                "Range end must be on or after range start",
                400,
                "INVALID_TIME_RANGE",
                {"range_start": normalized_start.isoformat(), "range_end": normalized_end.isoformat()},
            )
        return self.outage_repo.list_in_time_range(normalized_start, normalized_end)

    def _get_planned_outage_or_raise(self, outage_id: str) -> OutageEvent:
        outage = self.outage_repo.get_by_id(outage_id)
        if outage is None:
            raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})
        if outage.outage_type not in {"Planned"}:
            raise AppException("Only Planned outages are supported in Phase 1", 400, "UNSUPPORTED_OUTAGE_TYPE")
        return outage

    def process_due_outages(self) -> list[dict[str, object]]:
        """Batch job entrypoint: process due planned outages across the notification lifecycle."""
        results: list[dict[str, object]] = []
        due_notifications = self.get_due_lifecycle_notifications()
        for outage, notification_type in due_notifications:
            try:
                results.append(self.process_outage(outage.outage_id, notification_type))
            except Exception:  # noqa: BLE001 - batch should continue after a single outage failure.
                logger.exception("Planned outage batch item failed", extra={"ctx_outage_id": outage.outage_id})
                self.db.rollback()
        logger.info("Planned outage batch completed", extra={"ctx_processed": len(results), "ctx_run_at": ist_now()})
        return results

    def get_due_lifecycle_notifications(self, now: datetime | None = None) -> list[tuple[OutageEvent, str]]:
        """Return outage lifecycle notifications that are due and have not already been sent."""
        current_time = ensure_ist(now or ist_now())
        due: list[tuple[OutageEvent, str]] = []
        for outage in self.outage_repo.list_planned_lifecycle_candidates():
            notification_type = self._next_due_notification_type(outage, current_time)
            if notification_type is not None:
                due.append((outage, notification_type))
        return due

    def _next_due_notification_type(self, outage: OutageEvent, now: datetime) -> str | None:
        if outage.cancellation_flag:
            if not self._already_sent(outage.outage_id, "Cancellation Alert"):
                return "Cancellation Alert"
            return None

        status = outage.status.strip().lower()
        actual_end_time = ensure_ist(outage.actual_end_time)

        if (
            status in {"restored", "resolved"}
            or (actual_end_time is not None and actual_end_time <= now)
        ) and not self._already_sent(outage.outage_id, "Outage Restored"):
            return "Outage Restored"

        start_time = ensure_ist(outage.start_time)
        if start_time is None:
            return None

        if now >= start_time and not self._already_sent(outage.outage_id, "Outage Start"):
            return "Outage Start"

        if status != "scheduled":
            return None

        seconds_until_start = (start_time - now).total_seconds()

        # Reminder: 15 to 60 seconds before outage start
        #Reminder :0 
        if (
            0 < seconds_until_start <= 120
            and not self._already_sent(outage.outage_id, "Reminder")
            and self._advance_notice_was_sent_early_enough(outage.outage_id, now)
        ):
            return "Reminder"

        # Advance Notice: within 1 minute before outage start
        if (
            60 < seconds_until_start <= 180
            and not self._already_sent(outage.outage_id, "Advance Notice")
        ):
            return "Advance Notice"

        return None

    def _already_sent(self, outage_id: str, notification_type: str) -> bool:
        return self.notification_repo.exists_for_outage_type(outage_id, notification_type)

    #it will check whether advance notice was sent at least 30 seconds before the current time to allow for a reminder to be sent 15 seconds before the outage start. This ensures that the reminder is only sent if the advance notice was sent early enough to meet the timing requirements.
    def _advance_notice_was_sent_early_enough(self, outage_id: str, now: datetime) -> bool:
        sent_at = ensure_ist(self.notification_repo.latest_sent_at(outage_id, "Advance Notice"))
        if sent_at is None:
            return False
        return sent_at <= now - timedelta(minutes=1)
        # return sent_at <= now - timedelta(seconds=60)
