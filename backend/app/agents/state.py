from typing import TypedDict


class PlannedOutageState(TypedDict, total=False):
    """State passed between agent steps for planned outage processing."""

    outage_id: str
    notification_type: str
    affected_customers: list[dict[str, object]]
    affected_count: int
    medical_baseline_customers: int
    notifications_created: int
    notifications_delivered: int
    notifications_failed: int
    validation_status: str
