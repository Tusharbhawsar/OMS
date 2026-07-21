from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)   #it used to make the class immutable and hashable, which is useful for value objects like DeliveryResult.
class NotificationPayload:
    """Channel delivery input."""

    to: str
    subject: str | None
    message: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class DeliveryResult:
    """Provider delivery result normalized across channels."""

    provider_name: str
    status: str
    provider_message_id: str | None = None
    error_message: str | None = None


class Notifier(Protocol):
    """Notification provider interface."""

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        """Send a notification and return normalized delivery status."""
        ...
