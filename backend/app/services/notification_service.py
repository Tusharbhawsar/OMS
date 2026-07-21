import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.integrations.notifiers.base import NotificationPayload
from app.integrations.notifiers.factory import NotifierFactory
from app.models.notification import Notification, NotificationAttempt
from app.repositories.notification_repository import NotificationRepository
from app.repositories.outage_repository import OutageRepository
from app.services.llm_message_service import LlmMessageService
from app.utils.id_generator import generate_prefixed_id
from app.utils.time import ist_now

logger = logging.getLogger(__name__)


class NotificationService:
    """Creates notification records and dispatches sandbox messages."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.outage_repo = OutageRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.message_service = LlmMessageService()
        self.notifier_factory = NotifierFactory()

    def notify_customers(self, outage_id: str, notification_type: str, customers: list[dict[str, object]]) -> dict[str, int]:
        """Create and dispatch notifications for affected customers in priority order."""
        outage = self.outage_repo.get_by_id(outage_id)
        if outage is None:
            raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})

        created = 0
        delivered = 0
        failed = 0
        now = ist_now()

        for customer in customers:
            customer_id = str(customer["customer_id"])
            full_name = f"{customer['first_name']} {customer['last_name']}".strip()
            channel_name = str(customer["channel_name"])
            channel_id = str(customer["channel_id"])
            destination = get_destination_for_channel(channel_name, customer)
            message = self.message_service.build_message(outage, notification_type, customer)

            notification = Notification(
                notification_id=generate_prefixed_id("NTF"),
                outage_id=outage_id,
                customer_id=customer_id,
                notification_type=notification_type,
                channel_id=channel_id,
                status="Pending",
                sent_at=now,
                message_content=message,
            )
            self.notification_repo.add(notification)
            created += 1

            try:
                notifier = self.notifier_factory.get(channel_name)
                result = notifier.send(
                    NotificationPayload(
                        to=destination,
                        subject=f"Outage {notification_type}",
                        message=message,
                        metadata={"outage_id": outage_id, "customer_id": customer_id, "channel": channel_name},
                    )
                )
                notification.status = result.status
                if result.status == "Delivered":
                    notification.delivered_at = ist_now()
                    delivered += 1
                    self.outage_repo.mark_customer_notified(outage_id, customer_id)
                else:
                    failed += 1
                self.notification_repo.add_attempt(
                    NotificationAttempt(
                        notification_id=notification.notification_id,
                        provider_name=result.provider_name,
                        provider_message_id=result.provider_message_id,
                        status=result.status,
                        error_message=result.error_message,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                notification.status = "Failed"
                self.notification_repo.add_attempt(
                    NotificationAttempt(
                        notification_id=notification.notification_id,
                        provider_name="sandbox_unknown",
                        status="Failed",
                        error_message=str(exc),
                    )
                )
                logger.exception("Notification dispatch failed", extra={"ctx_outage_id": outage_id, "ctx_customer_id": customer_id})

        self.db.flush()
        logger.info(
            "Notifications processed",
            extra={"ctx_outage_id": outage_id, "ctx_created": created, "ctx_delivered": delivered, "ctx_failed": failed},
        )
        return {"created": created, "delivered": delivered, "failed": failed}


def get_destination_for_channel(channel_name: str, customer: dict[str, object]) -> str:
    """Resolve the delivery address for a given channel.

    Email -> the customer email (unchanged). Every other channel (SMS/WhatsApp/IVR)
    is a phone channel, so the number is normalized to E.164 which Twilio requires.
    """
    if channel_name.strip().lower() == "email":
        return str(customer.get("email") or "missing-email@example.local")
    return normalize_phone(str(customer.get("phone") or "+15550000000"))


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164 

    Rules (POC-simple):
      * already '+<digits>'  -> kept as-is (just stripped of separators)
      * '00' international prefix -> replaced with '+'
      * exactly 10 digits    -> treated as a national number, gets DEFAULT_COUNTRY_CODE
      * anything else        -> a leading '+' is added to the digits
    """
    import re

    raw = str(raw).strip()
    if raw.startswith("+"):
        return "+" + re.sub(r"\D", "", raw[1:])

    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00"):
        return "+" + digits[2:]
    if len(digits) == 10:
        return get_settings().default_country_code + digits
    return "+" + digits
