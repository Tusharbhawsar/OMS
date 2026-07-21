"""Twilio SMS adapter — sends a real text message via Twilio's REST API.

Used by NotifierFactory for the "SMS" channel when NOTIFICATION_MODE=provider.
Implements the same `Notifier` protocol (see base.py) as the sandbox adapters, so
NotificationService can call `.send(payload)` without knowing which backend it hit.

Uses `requests` directly (see twilio_client.py) — no Twilio SDK dependency.
"""

import logging

from app.core.config import get_settings
from app.integrations.notifiers.base import DeliveryResult, NotificationPayload
from app.integrations.notifiers.twilio_client import result_from_response, twilio_post

logger = logging.getLogger(__name__)

# Twilio message statuses that mean "accepted / on its way / delivered". Anything else
# (undelivered, failed) is treated as a failure. On create, Twilio usually returns
# "queued" or "accepted"; the final delivered/undelivered status arrives later via an
# async status-callback webhook (a possible Phase-2 enhancement).
_ACCEPTED_STATUSES = {"queued", "accepted", "sending", "sent", "delivered"}


class TwilioSmsNotifier:
    """Sends SMS through Twilio and returns a normalized DeliveryResult."""

    provider_name = "twilio_sms"

    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        # Fail-safe guard: no credentials -> do not call the network, just report Failed.
        # Mirrors SmtpEmailNotifier's "SMTP_HOST not configured" behavior.
        if not self.settings.twilio_account_sid:
            logger.warning("Twilio not configured (TWILIO_ACCOUNT_SID missing); SMS not sent")
            return DeliveryResult(self.provider_name, "Failed", error_message="Twilio not configured")

        try:
            resp = twilio_post(
                "Messages",
                {
                    "To": payload.to,                       # customer phone in E.164, e.g. +1...
                    "From": self.settings.twilio_sms_from,  # your Twilio (trial) number
                    "Body": payload.message,
                },
            )
            result = result_from_response(self.provider_name, resp, _ACCEPTED_STATUSES)
            logger.info("Twilio SMS attempt", extra={"ctx_to": payload.to, "ctx_status": result.status})
            return result
        except Exception as exc:  # noqa: BLE001 — never let a provider error crash the batch
            logger.error("Twilio SMS failed", exc_info=True, extra={"ctx_to": payload.to})
            return DeliveryResult(self.provider_name, "Failed", error_message=str(exc))
