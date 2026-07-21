from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success_response
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationOut
from app.utils.time import IST

router = APIRouter()


def serialize_notification_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.isoformat()


# def list_notifications(
#     outage_id: str | None = Query(default=None),
#     limit: int = Query(default=200, ge=1, le=1000),
#     db: Session = Depends(get_db),
# ) -> dict[str, object]:
#     """List notification records, optionally filtered by outage."""
#     notifications = NotificationRepository(db).list_by_outage(outage_id=outage_id, limit=limit)
#     data = [NotificationOut.model_validate(item).model_dump(mode="json") for item in notifications]
#     return success_response(200, "Notifications fetched successfully", data)

def list_notifications(
    outage_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """List notification records, optionally filtered by outage."""
    notifications = NotificationRepository(db).list_by_outage(outage_id=outage_id,limit=limit)
    data = []
    for item in notifications:
        notification_data = NotificationOut.model_validate(item).model_dump(mode="json")
        notification_data["sent_at"] = serialize_notification_datetime(item.sent_at)
        notification_data["delivered_at"] = serialize_notification_datetime(item.delivered_at)
        data.append(notification_data)
    return success_response(200,"Notifications fetched successfully",data)


router.add_api_route("", list_notifications, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs
