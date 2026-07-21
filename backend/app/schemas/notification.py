from datetime import datetime

from app.schemas.common import OrmModel


class NotificationOut(OrmModel):
    notification_id: str
    outage_id: str
    customer_id: str
    notification_type: str
    channel_id: str
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    message_content: str
