from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationAttempt
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for notification and provider attempt audit records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        return notification

    def add_attempt(self, attempt: NotificationAttempt) -> NotificationAttempt:
        self.db.add(attempt)
        return attempt

    def list_by_outage(self, outage_id: str | None = None, limit: int = 200) -> list[Notification]:
        stmt = select(Notification).order_by(Notification.sent_at.desc().nullslast()).limit(limit)
        if outage_id:
            stmt = stmt.where(Notification.outage_id == outage_id)
        return list(self.db.scalars(stmt).all())

    def exists_for_outage_type(self, outage_id: str, notification_type: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.outage_id == outage_id)
            .where(Notification.notification_type == notification_type)
        )
        return int(self.db.scalar(stmt) or 0) > 0

    def latest_sent_at(self, outage_id: str, notification_type: str) -> datetime | None:
        stmt = (
            select(func.max(Notification.sent_at))
            .where(Notification.outage_id == outage_id)
            .where(Notification.notification_type == notification_type)
        )
        return self.db.scalar(stmt)

    def count_by_status(self, status: str) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Notification).where(Notification.status == status)) or 0)

    def count_all(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Notification)) or 0)
