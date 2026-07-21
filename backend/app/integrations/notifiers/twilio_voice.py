"""Twilio Voice / IVR adapter — places an automated outbound call that reads the
outage message aloud using text-to-speech, via Twilio's REST API.

Used by NotifierFactory for the "IVR"/"Voice" channel when NOTIFICATION_MODE=provider.
This is the most valuable channel for Medical Baseline customers who may not use a
smartphone: the message is spoken over a normal phone call.

How it works: we pass a small TwiML document (a <Say> verb) inline in the `Twiml`
parameter of the Calls API, so there's no extra public webhook endpoint to host.

Uses `requests` directly (see twilio_client.py) — no Twilio SDK dependency.
"""

import logging
from xml.sax.saxutils import escape as xml_escape

from app.core.config import get_settings
from app.integrations.notifiers.base import DeliveryResult, NotificationPayload
from app.integrations.notifiers.twilio_client import result_from_response, twilio_post

logger = logging.getLogger(__name__)

# Call lifecycle statuses that mean the call was accepted/placed. Final answered/completed
# status arrives asynchronously; on create Twilio typically returns "queued".
_ACCEPTED_STATUSES = {"queued", "initiated", "ringing", "in-progress", "completed"}


class TwilioVoiceNotifier:
    """Places an IVR voice call through Twilio and returns a normalized DeliveryResult."""

    provider_name = "twilio_voice"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_twiml(self, message: str) -> str:
        """Build a minimal TwiML doc that speaks the message via text-to-speech.

        The message is XML-escaped so quotes/&/< in the text can't break the markup.
        """
        safe = xml_escape(message)
        lang = self.settings.twilio_voice_language
        return f'<?xml version="1.0" encoding="UTF-8"?><Response><Say language="{lang}">{safe}</Say></Response>'

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        # Fail-safe guard, consistent with the other Twilio adapters.
        if not self.settings.twilio_account_sid:
            logger.warning("Twilio not configured (TWILIO_ACCOUNT_SID missing); IVR call not placed")
            return DeliveryResult(self.provider_name, "Failed", error_message="Twilio not configured")

        try:
            resp = twilio_post(
                "Calls",
                {
                    "To": payload.to,                          # customer phone in E.164
                    "From": self.settings.twilio_voice_from,   # your Twilio (trial) caller ID
                    "Twiml": self._build_twiml(payload.message),
                },
            )
            result = result_from_response(self.provider_name, resp, _ACCEPTED_STATUSES)
            logger.info("Twilio IVR attempt", extra={"ctx_to": payload.to, "ctx_status": result.status})
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("Twilio IVR call failed", exc_info=True, extra={"ctx_to": payload.to})
            return DeliveryResult(self.provider_name, "Failed", error_message=str(exc))
