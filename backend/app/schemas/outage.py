from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import OrmModel


class OutageEventOut(OrmModel):
    outage_id: str
    outage_type: str
    status: str
    start_time: datetime | None
    estimated_end_time: datetime | None
    actual_end_time: datetime | None
    etr_predicted_by_ml: bool
    cancellation_flag: bool
    cancelled_at: datetime | None
    created_at: datetime


class AffectedCustomerOut(BaseModel):
    customer_id: str
    full_name: str
    email: str | None
    phone: str | None
    channel_name: str
    customer_type: str
    priority: int
    is_medical_baseline: bool
    service_point_id: str
    circuit_id: str
    transformer_id: str
