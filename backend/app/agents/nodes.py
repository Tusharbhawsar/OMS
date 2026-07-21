from sqlalchemy.orm import Session

from app.agents.state import PlannedOutageState
from app.core.exceptions import AppException
from app.repositories.outage_repository import OutageRepository
from app.services.customer_mapping_service import CustomerMappingService
from app.services.notification_service import NotificationService


class PlannedOutageAgentNodes:
    """Agent step functions for deterministic planned outage processing."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.outage_repo = OutageRepository(db)
        self.mapping_service = CustomerMappingService(db)
        self.notification_service = NotificationService(db)

    #this will extract the only planned outage and validate it, if not found or not planned it will throw error and stop the workflow
    def validate_outage(self, state: PlannedOutageState) -> PlannedOutageState:
        outage_id = state["outage_id"]
        outage = self.outage_repo.get_by_id(outage_id)
        if outage is None:
            raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})
        if outage.outage_type not in {"Planned"}:
            raise AppException("Only Planned outages are supported in Phase 1", 400, "UNSUPPORTED_OUTAGE_TYPE")
        state["validation_status"] = "valid"
        return state

    #
    def identify_customers(self, state: PlannedOutageState) -> PlannedOutageState:
        customers = self.mapping_service.identify_affected_customers(state["outage_id"])
        state["affected_customers"] = customers
        state["affected_count"] = len(customers)
        state["medical_baseline_customers"] = sum(1 for c in customers if bool(c.get("is_medical_baseline")))
        return state

    def dispatch_notifications(self, state: PlannedOutageState) -> PlannedOutageState:
        result = self.notification_service.notify_customers(
            outage_id=state["outage_id"],
            notification_type=state["notification_type"],
            customers=state.get("affected_customers", []),
        )
        state["notifications_created"] = result["created"]
        state["notifications_delivered"] = result["delivered"]
        state["notifications_failed"] = result["failed"]
        return state
