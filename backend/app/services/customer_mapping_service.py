import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.repositories.outage_repository import OutageRepository

logger = logging.getLogger(__name__)


class CustomerMappingService:
    """Identifies affected customers based on outage circuit/transformer mapping."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.outage_repo = OutageRepository(db)

    def identify_affected_customers(self, outage_id: str, *, persist: bool = True) -> list[dict[str, object]]:
        """Find, persist, and return affected customers in notification priority order."""
        outage = self.outage_repo.get_by_id(outage_id)
        if outage is None:
            raise AppException("Outage not found", 404, "OUTAGE_NOT_FOUND", {"outage_id": outage_id})

        customers = self.outage_repo.get_affected_customers(outage_id)
        if persist and not self.outage_repo.get_mapped_affected_customers(outage_id):
            for customer in customers:
                self.outage_repo.upsert_outage_customer(outage_id, str(customer["customer_id"]))
            self.db.flush()

        logger.info(
            "Affected customer mapping completed",
            extra={"ctx_outage_id": outage_id, "ctx_affected_customers": len(customers)},
        )
        return customers
