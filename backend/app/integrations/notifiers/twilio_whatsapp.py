"""Twilio WhatsApp adapter — sends a WhatsApp message via Twilio's REST API.

Used by NotifierFactory for the "WhatsApp" channel when NOTIFICATION_MODE=provider.
It hits the SAME Messages endpoint as SMS; the only differences are:
  * both To and From must carry the "whatsapp:" prefix, and
  * on a paid account, business-initiated messages must use a pre-approved template
    (on the free sandbox you first "join" by texting the sandbox code from your phone).

Uses `requests` directly (see twilio_client.py) — no Twilio SDK dependency.
"""

import logging

from app.core.config import get_settings
from app.integrations.notifiers.base import DeliveryResult, NotificationPayload
from app.integrations.notifiers.twilio_client import result_from_response, twilio_post

logger = logging.getLogger(__name__)

_ACCEPTED_STATUSES = {"queued", "accepted", "sending", "sent", "delivered", "read"}


def _as_whatsapp_address(value: str) -> str:
    """Ensure an address has the 'whatsapp:' prefix Twilio requires.

    The customer record stores a plain phone number, so we add the prefix here rather
    than changing the shared destination-resolution logic in NotificationService.
    """
    value = value.strip()
    return value if value.startswith("whatsapp:") else f"whatsapp:{value}"


class TwilioWhatsAppNotifier:
    """Sends WhatsApp messages through Twilio and returns a normalized DeliveryResult."""

    provider_name = "twilio_whatsapp"

    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        # Fail-safe guard, identical in spirit to the SMS adapter.
        if not self.settings.twilio_account_sid:
            logger.warning("Twilio not configured (TWILIO_ACCOUNT_SID missing); WhatsApp not sent")
            return DeliveryResult(self.provider_name, "Failed", error_message="Twilio not configured")

        try:
            resp = twilio_post(
                "Messages",
                {
                    "To": _as_whatsapp_address(payload.to),
                    "From": _as_whatsapp_address(self.settings.twilio_whatsapp_from),
                    "Body": payload.message,
                    # NOTE: for production business-initiated WhatsApp, send an approved
                    # template via ContentSid/ContentVariables instead of Body.
                },
            )
            result = result_from_response(self.provider_name, resp, _ACCEPTED_STATUSES)
            logger.info("Twilio WhatsApp attempt", extra={"ctx_to": payload.to, "ctx_status": result.status})
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("Twilio WhatsApp failed", exc_info=True, extra={"ctx_to": payload.to})
            return DeliveryResult(self.provider_name, "Failed", error_message=str(exc))
