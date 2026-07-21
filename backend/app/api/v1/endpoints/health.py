from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success_response

router = APIRouter()


def readiness(db: Session = Depends(get_db)) -> dict[str, object]:
    """Readiness check that validates database connectivity."""
    db.execute(text("SELECT 1"))
    return success_response(200, "Service is ready", {"database": "connected"})


router.add_api_route("/ready", readiness, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs
