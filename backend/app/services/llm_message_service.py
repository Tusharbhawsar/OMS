import logging

from app.core.config import get_settings
from app.integrations.llm.gemini_client import get_gemini_client
from app.models.outage import OutageEvent
from app.services.message_template_service import MessageTemplateService, format_datetime

logger = logging.getLogger(__name__)

# ISO-639-1 code -> human name used in the prompt. Unknown codes fall back to English.
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
}

# Per notification type, which formatted fact tokens MUST appear verbatim in the
# LLM output. If any required token is missing we reject the output and fall back
# to the deterministic template, so customers never get a message with a wrong or
# hallucinated date/time.
REQUIRED_FACTS = {
    "Advance Notice": ("start", "etr"),
    "Reminder": ("start", "etr"),
    "Outage Start": ("etr",),
    "Outage Restored": (),
    "Cancellation Alert": ("start",),
}

MAX_MESSAGE_CHARS = 600

# Low temperature for fact fidelity (auth.json defaults to 0.9, too creative for
# notifications where dates/times must be copied verbatim).
GENERATION_TEMPERATURE = 0.2


class LlmMessageService:
    """Generates smart, personalized, multilingual notification messages via Gemini.

    Falls back to the deterministic MessageTemplateService whenever the LLM is
    unavailable, errors, or returns output that fails the fact-preservation guardrail.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.template_service = MessageTemplateService()
        self.client = get_gemini_client()

    def build_message(
        self,
        outage: OutageEvent,
        notification_type: str,
        customer: dict[str, object],
    ) -> str:
        """Return the message text for a customer, using Gemini with a safe fallback."""
        customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        language_code = str(customer.get("preferred_language") or self.settings.default_language).lower()

        # Fast path: English template requires no LLM; only reach for the model when it
        # adds value (a non-default language or personalization). English non-medical
        # messages still go through the LLM for tone, but degrade cleanly if it fails.
        if not self.client.available:
            return self._fallback(outage, notification_type, customer_name, language_code)

        start = format_datetime(outage.start_time)
        etr = format_datetime(outage.estimated_end_time)
        facts = {"start": start, "etr": etr}

        try:
            system_instruction = self._system_instruction(language_code, customer)
            prompt = self._build_prompt(outage, notification_type, customer_name, customer, start, etr)
            message = self.client.generate(
                prompt,
                system_instruction=system_instruction,
                temperature=GENERATION_TEMPERATURE,
            )

            if self._is_valid(message, notification_type, facts):
                logger.info(
                    "LLM message generated",
                    extra={
                        "ctx_outage_id": outage.outage_id,
                        "ctx_notification_type": notification_type,
                        "ctx_language": language_code,
                        "ctx_medical_baseline": bool(customer.get("is_medical_baseline")),
                    },
                )
                return message

            logger.warning(
                "LLM message failed guardrail; using template fallback",
                extra={"ctx_outage_id": outage.outage_id, "ctx_notification_type": notification_type},
            )
        except Exception:  # noqa: BLE001 - any LLM failure degrades to the template.
            logger.exception(
                "LLM message generation failed; using template fallback",
                extra={"ctx_outage_id": outage.outage_id, "ctx_notification_type": notification_type},
            )

        return self._fallback(outage, notification_type, customer_name, language_code)

    def _fallback(self, outage: OutageEvent, notification_type: str, customer_name: str, language_code: str) -> str:
        """Deterministic template message. If the LLM is up, translate it to the
        target language; otherwise return the English template as-is."""
        base = self.template_service.build_message(outage, notification_type, customer_name)
        if language_code == "en" or language_code not in LANGUAGE_NAMES or not self.client.available:
            return base
        try:
            language_name = LANGUAGE_NAMES[language_code]
            translated = self.client.generate(
                f"Translate the following power-outage notification into {language_name}. "
                f"Keep every date, time, and name EXACTLY as written. Output only the translation:\n\n{base}"
            )
            return translated or base
        except Exception:  # noqa: BLE001
            return base

    def _system_instruction(self, language_code: str, customer: dict[str, object]) -> str:
        language_name = LANGUAGE_NAMES.get(language_code, "English")
        channel = str(customer.get("channel_name") or "").strip().lower()
        length_hint = (
            "Keep it under 160 characters (SMS)."
            if channel == "sms"
            else "Keep it under 320 characters; a brief greeting is fine."
        )
        medical_clause = (
            "This customer is on the Medical Baseline program and may rely on electricity for "
            "medical equipment. Add one short, calm but urgent line advising them to prepare a "
            "backup power option or contact support if needed."
            if bool(customer.get("is_medical_baseline"))
            else ""
        )
        return (
            "You write customer notifications for a power utility company. "
            f"Write the message in {language_name}. "
            "Output ONLY the message text — no quotes, no markdown, no preamble. "
            f"{length_hint} "
            "Copy every date, time, and ID EXACTLY as given; do not reformat, localize, or translate them. "
            "Never invent facts that are not provided. Be clear, polite, and reassuring. "
            f"{medical_clause}"
        ).strip()

    def _build_prompt(
        self,
        outage: OutageEvent,
        notification_type: str,
        customer_name: str,
        customer: dict[str, object],
        start: str,
        etr: str,
    ) -> str:
        lines = [f"Write a '{notification_type}' power outage notification.", "", "Facts:"]
        lines.append(f"- Customer name: {customer_name}")
        if notification_type in {"Advance Notice", "Reminder", "Cancellation Alert"}:
            lines.append(f"- Scheduled start time: {start}")
        if notification_type in {"Advance Notice", "Reminder", "Outage Start"}:
            lines.append(f"- Estimated restoration: {etr}")
        if notification_type == "Outage Restored":
            lines.append("- Power has been restored.")
        if notification_type == "Cancellation Alert":
            lines.append("- The outage has been cancelled; no action needed.")
        region = customer.get("geographic_region")
        if region:
            lines.append(f"- Area/region: {region}")
        segment = customer.get("type_name")
        if segment:
            lines.append(f"- Customer segment: {segment}")
        lines.append(f"- Current outage status: {outage.status}")
        return "\n".join(lines)

    def _is_valid(self, message: str, notification_type: str, facts: dict[str, str]) -> bool:
        if not message or not message.strip():
            return False
        if len(message) > MAX_MESSAGE_CHARS:
            return False
        for fact_key in REQUIRED_FACTS.get(notification_type, ()):
            token = facts.get(fact_key)
            # A formatted token is "YYYY-MM-DD HH:MM"; require both the date and the
            # time to appear (not necessarily contiguous) so minor rephrasing passes
            # but a missing/altered date or time is still rejected.
            if not token:
                continue
            parts = token.split()
            if any(part not in message for part in parts):
                return False
        return True
