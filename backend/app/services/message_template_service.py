from datetime import datetime

from app.models.outage import OutageEvent
from app.utils.time import format_ist_datetime


class MessageTemplateService:
    """Deterministic customer-facing templates for notification journeys."""

    def build_message(self, outage: OutageEvent, notification_type: str, customer_name: str) -> str:
        start = format_datetime(outage.start_time)
        etr = format_datetime(outage.estimated_end_time)
        if notification_type == "Advance Notice":
            return f"Hello {customer_name}, a planned power outage is scheduled for {start}. Estimated restoration: {etr}."
        if notification_type == "Reminder":
            return f"Reminder: your planned power outage is scheduled for {start}. Estimated restoration: {etr}."
        if notification_type == "Outage Start":
            return f"Power outage has started in your area. Estimated restoration: {etr}."
        if notification_type == "Outage Restored":
            return "Power has been restored in your area. Thank you for your patience."
        if notification_type == "Cancellation Alert":
            return f"The scheduled outage for {start} has been cancelled. No action is required."
        return f"Outage update: status={outage.status}, estimated restoration={etr}."


def format_datetime(value: datetime | None) -> str:
    """Format a datetime for customer-facing messages."""
    return format_ist_datetime(value)
