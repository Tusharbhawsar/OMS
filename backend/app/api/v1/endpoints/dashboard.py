from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success_response
from app.services.dashboard_service import DashboardService

router = APIRouter()


def get_dashboard_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return KPI summary for React/Streamlit dashboard."""
    data = DashboardService(db).get_summary()
    return success_response(200, "Dashboard summary fetched successfully", data)


def get_active_outage_rows(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return active outage rows for dashboard tables/maps."""
    data = DashboardService(db).get_active_outages()
    return success_response(200, "Active outage dashboard rows fetched successfully", data)


router.add_api_route("/summary", get_dashboard_summary, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs

#Active planned outages
router.add_api_route("/active-outages", get_active_outage_rows, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs