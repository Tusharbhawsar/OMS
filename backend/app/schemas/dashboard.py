from pydantic import BaseModel


class DashboardSummary(BaseModel):
    active_outages: int
    scheduled_pending: int
    cancelled_outages: int
    completed_outages: int
    next_scheduled_outage_id: str | None
    next_scheduled_start: str | None
    seconds_until_next_scheduled: int | None
    total_outages: int
    affected_customers: int
    medical_baseline_pending: int
    notifications_sent: int
    notifications_delivered: int
    notifications_failed: int
    delivery_rate_percent: float


class ActiveOutageRow(BaseModel):
    outage_id: str
    outage_type: str
    status: str
    region: str | None
    affected_customers: int
    medical_baseline_customers: int
    notifications_sent: int
    start_time: str | None
    estimated_end_time: str | None
