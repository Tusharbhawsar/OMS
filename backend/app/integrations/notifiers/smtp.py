import logging
import smtplib
from email.message import EmailMessage
from uuid import uuid4

from app.core.config import get_settings
from app.integrations.notifiers.base import DeliveryResult, NotificationPayload

logger = logging.getLogger(__name__)


class SmtpEmailNotifier:
    """SMTP email adapter for sending real emails."""

    provider_name = "smtp_email"

    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        if not self.settings.smtp_host:
            logger.warning("SMTP_HOST not configured, falling back to log-only")
            return DeliveryResult(
                provider_name=self.provider_name,
                status="Failed",
                error_message="SMTP_HOST not configured",
            )

        msg = EmailMessage()
        msg.set_content(payload.message)
        msg["Subject"] = payload.subject or "Notification"
        msg["From"] = self.settings.smtp_from_email
        msg["To"] = payload.to

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if self.settings.smtp_tls:
                    server.starttls()
                if self.settings.smtp_user and self.settings.smtp_password:
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)

            logger.info("SMTP email delivered", extra={"ctx_to": payload.to, "ctx_subject": payload.subject})
            return DeliveryResult(
                provider_name=self.provider_name,
                status="Delivered",
                provider_message_id=f"smtp_{uuid4().hex}",
            )
        except Exception as e:
            logger.error("Failed to send SMTP email", exc_info=True, extra={"ctx_to": payload.to})
            return DeliveryResult(
                provider_name=self.provider_name,
                status="Failed",
                error_message=str(e),
            )
