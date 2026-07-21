from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.response import success_response
from app.repositories.outage_repository import OutageRepository
from app.schemas.outage import OutageEventOut
from app.services.customer_mapping_service import CustomerMappingService
from app.services.outage_lifecycle_rules import (
    RESTORED_STATUSES,
    apply_cancellation,
    apply_restoration,
    is_live_status,
    normalize_status,
)
from app.services.planned_outage_service import PlannedOutageService
from app.utils.time import ist_now

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


def cancel_outage(outage_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Cancel a planned outage as an event (Option 3).

    Real cancellations arrive *after* an outage is scheduled, so this endpoint is how the
    system learns about them: it flips cancellation_flag/status and stamps cancelled_at.
    The existing lifecycle rule then fires the "Cancellation Alert" reactively. Only a
    still-live outage (Scheduled/Active) can be cancelled; a finished one cannot. Repeating
    the call on an already-cancelled outage is idempotent.
    """
    repo = OutageRepository(db)
    outage = repo.get_by_id(outage_id)
    if outage is None:
        raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})

    if outage.cancellation_flag or normalize_status(outage.status) == "cancelled":
        data = OutageEventOut.model_validate(outage).model_dump(mode="json")
        return success_response(200, "Outage already cancelled", data)

    if not is_live_status(outage.status):
        raise AppException(
            "Only a scheduled or active outage can be cancelled",
            409,
            "OUTAGE_NOT_CANCELLABLE",
            {"outage_id": outage_id, "status": outage.status},
        )

    apply_cancellation(outage, ist_now())
    db.commit()
    db.refresh(outage)
    data = OutageEventOut.model_validate(outage).model_dump(mode="json")
    return success_response(200, "Outage cancelled successfully", data)


def restore_outage(outage_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Restore a planned outage as an event (Option 3, restoration counterpart).

    Power being restored is a real-world event that arrives *after* the outage is under way,
    so this endpoint is how the system learns the actual end: it stamps actual_end_time and
    moves the status to Restored. The lifecycle then fires the "Outage Restored" alert
    reactively. This is the legitimate way to fill actual_end_time, which the importer
    refuses to set on a still-live outage. Only a live outage (Scheduled/Active) can be
    restored; a cancelled/finished one cannot. Repeating the call is idempotent.
    """
    repo = OutageRepository(db)
    outage = repo.get_by_id(outage_id)
    if outage is None:
        raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})

    if outage.actual_end_time is not None or normalize_status(outage.status) in RESTORED_STATUSES:
        data = OutageEventOut.model_validate(outage).model_dump(mode="json")
        return success_response(200, "Outage already restored", data)

    if not is_live_status(outage.status):
        raise AppException(
            "Only a scheduled or active outage can be restored",
            409,
            "OUTAGE_NOT_RESTORABLE",
            {"outage_id": outage_id, "status": outage.status},
        )

    apply_restoration(outage, ist_now())
    db.commit()
    db.refresh(outage)
    data = OutageEventOut.model_validate(outage).model_dump(mode="json")
    return success_response(200, "Outage restored successfully", data)


router.add_api_route("/active", list_active_outages, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs
router.add_api_route("/batch/process-planned", process_planned_batch, methods=["POST"], status_code=status.HTTP_202_ACCEPTED,include_in_schema=True)
router.add_api_route("/{outage_id}/affected-customers", get_affected_customers, methods=["GET"],include_in_schema=True)
router.add_api_route("/{outage_id}/process-planned", process_planned_outage, methods=["POST"], status_code=status.HTTP_202_ACCEPTED,include_in_schema=True)
router.add_api_route("/{outage_id}/cancel", cancel_outage, methods=["POST"], include_in_schema=True)  # Option 3: cancellation as an event
router.add_api_route("/{outage_id}/restore", restore_outage, methods=["POST"], include_in_schema=True)  # Option 3: restoration as an event