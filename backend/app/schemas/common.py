from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    """Base schema that can read SQLAlchemy model objects."""

    model_config = ConfigDict(from_attributes=True)


class HealthData(BaseModel):
    service: str


class ProcessingResult(BaseModel):
    outage_id: str
    notification_type: str
    affected_customers: int
    notifications_created: int
    notifications_delivered: int
    medical_baseline_customers: int
    processed_at: datetime
