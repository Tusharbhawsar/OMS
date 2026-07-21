import logging
from uuid import uuid4

from app.integrations.notifiers.base import DeliveryResult, NotificationPayload

logger = logging.getLogger(__name__)


class SandboxEmailNotifier:
    """Sandbox email adapter used in Phase 1. Logs delivery without calling SendGrid."""

    provider_name = "sandbox_email"

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        logger.info(
            "Sandbox email delivered",
            extra={"ctx_to": payload.to, "ctx_subject": payload.subject, "ctx_channel": "Email"},
        )
        return DeliveryResult(provider_name=self.provider_name, status="Delivered", provider_message_id=f"email_{uuid4().hex}")


class SandboxSmsNotifier:
    """Sandbox SMS adapter used in Phase 1. Logs delivery without calling Twilio."""

    provider_name = "sandbox_sms"

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        logger.info("Sandbox SMS delivered", extra={"ctx_to": payload.to, "ctx_channel": "SMS"})
        return DeliveryResult(provider_name=self.provider_name, status="Delivered", provider_message_id=f"sms_{uuid4().hex}")


class SandboxGenericNotifier:
    """Generic simulator for non-Phase-1 channels such as IVR and App Push."""

    def __init__(self, channel_name: str) -> None:
        self.provider_name = f"sandbox_{channel_name.lower().replace(' ', '_')}"
        self.channel_name = channel_name

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        logger.info("Sandbox generic notification delivered", extra={"ctx_to": payload.to, "ctx_channel": self.channel_name})
        return DeliveryResult(provider_name=self.provider_name, status="Delivered", provider_message_id=f"generic_{uuid4().hex}")
