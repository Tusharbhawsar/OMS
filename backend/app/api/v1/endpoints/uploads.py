from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.response import success_response
from app.models.outage import OutageEvent, RawOutageEvent
from app.services.file_ingestion_service import FileIngestionService

router = APIRouter()

REBASED_DIR = BACKEND_DIR / "sample_data" / "rebased"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def upload_outage_data(
    file: UploadFile = File(...),
    # test_mode: bool | None = None,
    update_data: bool | None = None,
    reset_database: bool | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    # """Upload Phase-1 Excel/CSV data and import it into PostgrSQL.

    # Pass ?test_mode=true to rebase the uploaded outage times to "now + offset" (IST)
    # at import, so notifications fall due without hand-editing the file. Pass ?reset=true
    # to wipe all existing data first so the file fully replaces it (not merges).
    # When omitted, the global DEV_REBASE_TIMES / DEV_RESET_ON_UPLOAD settings decide.
    # """
    """Upload Phase-1 data (Excel/CSV) into PostgreSQL
    update_data=true : Shifts outage times to now so notifications trigger immediately
    reset_database=true : Wipes old  data to replace it (prevents merging)."""

    content = file.file.read()
    result = FileIngestionService(db, rebase_times=update_data, reset_on_upload=reset_database).import_upload(
        file.filename or "upload", content
    )
    return success_response(status.HTTP_201_CREATED, "Outage data imported successfully", result)


def download_rebased_file(name: str | None = None) -> FileResponse:
    """Download a rebased outage workbook saved during a test-mode upload.

    Without ?name=, returns the most recently saved rebased file. With ?name=, it
    accepts the original filename, its stem, or the rebased filename. Lets you fetch
    the file from the deployed server (where it lives on the server's disk) instead of
    only seeing it locally.
    """
    if not REBASED_DIR.exists():
        raise AppException("No rebased files available yet", 404, "REBASED_FILE_NOT_FOUND")

    if name:
        # Path(...).name strips any directory components to prevent path traversal.
        safe_name = Path(name).name
        candidates = [REBASED_DIR / safe_name, REBASED_DIR / f"{Path(safe_name).stem}_rebased.xlsx"]
        target = next((candidate for candidate in candidates if candidate.is_file()), None)
        if target is None:
            raise AppException("Rebased file not found", 404, "REBASED_FILE_NOT_FOUND", {"name": name})
    else:
        files = sorted(REBASED_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            raise AppException("No rebased files available yet", 404, "REBASED_FILE_NOT_FOUND")
        target = files[0]

    return FileResponse(path=target, filename=target.name, media_type=XLSX_MEDIA_TYPE)


def get_ingestion_status(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return backend-owned outage ingestion status for dashboards."""
    total_records = db.query(func.count(OutageEvent.outage_id)).scalar() or 0
    active_records = db.query(func.count(OutageEvent.outage_id)).filter(OutageEvent.status.in_(["Active", "Planned"])).scalar() or 0
    raw_events = db.query(func.count(RawOutageEvent.raw_event_id)).scalar() or 0
    last_received_at = db.query(func.max(RawOutageEvent.received_at)).scalar()

    data = {
        "status": "Healthy" if total_records else "Waiting for feed",
        "source": "Backend system feed",
        "mode": "system_ingestion",
        "total_records": int(total_records),
        "active_records": int(active_records),
        "raw_events": int(raw_events),
        "last_received_at": last_received_at.isoformat() if last_received_at else None,
    }
    return success_response(200, "Ingestion status fetched successfully", data)


router.add_api_route("/outage-data", upload_outage_data, methods=["POST"], status_code=status.HTTP_201_CREATED,include_in_schema=True)  # Hide from OpenAPI docs
router.add_api_route("/rebased-file", download_rebased_file, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs
router.add_api_route("/ingestion-status", get_ingestion_status, methods=["GET"],include_in_schema=True)  # Hide from OpenAPI docs