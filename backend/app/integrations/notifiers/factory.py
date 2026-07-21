from app.core.config import get_settings
from app.integrations.notifiers.base import Notifier
from app.integrations.notifiers.sandbox import SandboxEmailNotifier, SandboxGenericNotifier, SandboxSmsNotifier
from app.integrations.notifiers.smtp import SmtpEmailNotifier


class NotifierFactory:
    """Resolve channel-specific notification adapter."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get(self, channel_name: str) -> Notifier:
        normalized = channel_name.strip().lower()
        if normalized == "email":
            if self.settings.email_backend == "smtp":
                return SmtpEmailNotifier()
            return SandboxEmailNotifier()
        if normalized == "sms":
            return SandboxSmsNotifier()
        return SandboxGenericNotifier(channel_name=channel_name)
