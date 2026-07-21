from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success_response
from app.repositories.outage_repository import OutageRepository
from app.schemas.outage import ActualEndTimeIn, CancellationIn, OutageEventOut
from app.services.customer_mapping_service import CustomerMappingService
from app.services.planned_outage_service import PlannedOutageService

router = APIRouter()


def list_active_outages(db: Session = Depends(get_db)) -> dict[str, object]:
    """List active/scheduled outages for operations UI."""
    outages = OutageRepository(db).list_active()
    data = []
    for outage in outages:
        outage_data = OutageEventOut.model_validate(outage).model_dump(mode="json")
        data.append(outage_data)
    return success_response(200,"Active outages fetched successfully",data)


def get_affected_customers(outage_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Identify affected customers and show Medical Baseline priority order."""
    customers = CustomerMappingService(db).identify_affected_customers(outage_id, persist=False)
    return success_response(200, "Affected customers identified successfully", customers)


def list_outages_in_range(
    start: datetime = Query(..., description="Range start (inclusive), IST e.g. 2026-06-30T00:00:00"),
    end: datetime | None = Query(default=None, description="Range end (inclusive), IST. Omit for open-ended."),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """List all outages whose start time falls within the given time range."""
    outages = PlannedOutageService(db).list_outages_in_range(start, end)
    data = [OutageEventOut.model_validate(outage).model_dump(mode="json") for outage in outages]
    return success_response(200, "Outages in time range fetched successfully", data)


def record_actual_end_time(
    outage_id: str,
    payload: ActualEndTimeIn,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Field person reports the actual on-site restoration time for an outage."""
    outage = PlannedOutageService(db).record_actual_end_time(outage_id, payload.actual_end_time)
    data = OutageEventOut.model_validate(outage).model_dump(mode="json")
    return success_response(200, "Actual end time recorded successfully", data)


def set_cancellation_flag(
    outage_id: str,
    payload: CancellationIn,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Raise or revoke the cancellation flag for a planned outage."""
    outage = PlannedOutageService(db).set_cancellation_flag(outage_id, payload.cancellation_flag)
    data = OutageEventOut.model_validate(outage).model_dump(mode="json")
    message = "Outage marked for cancellation" if payload.cancellation_flag else "Cancellation flag cleared"
    return success_response(200, message, data)


def process_planned_outage(
    outage_id: str,
    notification_type: str = Query(default="Advance Notice"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Run LangGraph workflow: validate outage, map customers, dispatch sandbox notifications."""
    result = PlannedOutageService(db).process_outage(outage_id, notification_type)
    return success_response(status.HTTP_202_ACCEPTED, "Planned outage processing completed", result)


def process_planned_batch(db: Session = Depends(get_db)) -> dict[str, object]:
    """Run the planned outage batch job manually."""
    results = PlannedOutageService(db).process_due_outages()
    return success_response(status.HTTP_202_ACCEPTED, "Planned outage batch completed", results)


router.add_api_route("/active", list_active_outages, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs
router.add_api_route("/range", list_outages_in_range, methods=["GET"], include_in_schema=True)
router.add_api_route("/batch/process-planned", process_planned_batch, methods=["POST"], status_code=status.HTTP_202_ACCEPTED,include_in_schema=True)
router.add_api_route("/{outage_id}/affected-customers", get_affected_customers, methods=["GET"],include_in_schema=True)
router.add_api_route("/{outage_id}/actual-end-time", record_actual_end_time, methods=["PATCH"], include_in_schema=True)
router.add_api_route("/{outage_id}/cancellation-flag", set_cancellation_flag, methods=["PATCH"], include_in_schema=True)
router.add_api_route("/{outage_id}/process-planned", process_planned_outage, methods=["POST"], status_code=status.HTTP_202_ACCEPTED,include_in_schema=True)