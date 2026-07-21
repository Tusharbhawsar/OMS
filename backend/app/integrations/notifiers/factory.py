from app.core.config import get_settings
from app.integrations.notifiers.base import Notifier
from app.integrations.notifiers.sandbox import SandboxEmailNotifier, SandboxGenericNotifier, SandboxSmsNotifier
from app.integrations.notifiers.smtp import SmtpEmailNotifier
from app.integrations.notifiers.twilio_sms import TwilioSmsNotifier
from app.integrations.notifiers.twilio_voice import TwilioVoiceNotifier
from app.integrations.notifiers.twilio_whatsapp import TwilioWhatsAppNotifier


class NotifierFactory:
    """Resolve channel-specific notification adapter."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get(self, channel_name: str) -> Notifier:
        normalized = channel_name.strip().lower()

        # Email is independent of the SMS/voice provider: it always uses SMTP or the
        # email sandbox (Twilio has no email product), controlled by EMAIL_BACKEND.
        if normalized == "email":
            if self.settings.email_backend == "smtp":
                return SmtpEmailNotifier()
            return SandboxEmailNotifier()

        # When NOTIFICATION_MODE=provider, SMS / WhatsApp / IVR go through Twilio for
        # real delivery. In the default "sandbox" mode we fall through to the simulated
        # adapters below, so the POC still runs end-to-end without any Twilio credentials.
        if self.settings.notification_mode == "provider":
            if normalized == "sms":
                return TwilioSmsNotifier()
            if normalized == "whatsapp":
                return TwilioWhatsAppNotifier()
            if normalized in ("ivr", "voice"):
                return TwilioVoiceNotifier()

        # Sandbox fallbacks (default POC behavior).
        if normalized == "sms":
            return SandboxSmsNotifier()
        return SandboxGenericNotifier(channel_name=channel_name)
