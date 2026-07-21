from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository


class DashboardService:
    """Dashboard data service for React/Streamlit UI."""

    def __init__(self, db: Session) -> None:
        self.repo = DashboardRepository(db)

    def get_summary(self) -> dict[str, object]:
        row = self.repo.summary()
        sent = row["notifications_sent"]
        delivered = row["notifications_delivered"]
        row["delivery_rate_percent"] = round((delivered / sent) * 100, 2) if sent else 0.0
        return row

    def get_active_outages(self) -> list[dict[str, object]]:
        rows = self.repo.active_outage_rows()
        for row in rows:
            if row.get("start_time") is not None:
                row["start_time"] = row["start_time"].isoformat()
            if row.get("estimated_end_time") is not None:
                row["estimated_end_time"] = row["estimated_end_time"].isoformat()
            row["affected_customers"] = int(row.get("affected_customers") or 0)
            row["medical_baseline_customers"] = int(row.get("medical_baseline_customers") or 0)
            row["notifications_sent"] = int(row.get("notifications_sent") or 0)
        return rows
