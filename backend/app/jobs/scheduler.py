import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.planned_outage_service import PlannedOutageService
from app.utils.time import IST

logger = logging.getLogger(__name__)


class PlannedOutageScheduler:
    """APScheduler wrapper for planned outage batch processing."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.scheduler = BackgroundScheduler(timezone=IST)

    def start(self) -> None:
        self.scheduler.add_job(
            self._run_batch,
            trigger="interval",
            minutes=self.settings.batch_interval_minutes,
            id="planned_outage_batch",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _run_batch(self) -> None:
        db = SessionLocal()
        try:
            PlannedOutageService(db).process_due_outages()
        except Exception:  # noqa: BLE001
            logger.exception("Scheduled planned outage batch failed")
            db.rollback()
        finally:
            db.close()
