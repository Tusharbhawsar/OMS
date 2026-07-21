import logging
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, get_settings
from app.core.exceptions import AppException
from app.models.customer import Customer, CustomerServicePoint, ServicePoint
from app.models.notification import Notification, NotificationAttempt
from app.models.outage import OutageCircuitMap, OutageCustomerMap, OutageEvent, RawOutageEvent
from app.models.reference import ChannelMaster, CustomerType
from app.utils.time import ist_now

logger = logging.getLogger(__name__)


class FileIngestionService:
    """Service responsible for importing Phase-1 outage Excel/CSV data."""

    MODEL_BY_SHEET = {
        "CUSTOMER": Customer,
        "SERVICE_POINT": ServicePoint,
        "CUSTOMER_TYPE": CustomerType,
        "CHANNEL_MASTER": ChannelMaster,
        "OUTAGE_EVENT": OutageEvent,
        "CUSTOMER_SERVICE_POINT": CustomerServicePoint,
        "OUTAGE_CIRCUIT_MAP": OutageCircuitMap,
        "OUTAGE_CUSTOMER_MAP": OutageCustomerMap,
    }

    PRIMARY_KEYS = {
        "CUSTOMER": ["customer_id"],
        "SERVICE_POINT": ["service_point_id"],
        "CUSTOMER_TYPE": ["customer_type_id"],
        "CHANNEL_MASTER": ["channel_id"],
        "OUTAGE_EVENT": ["outage_id"],
        "CUSTOMER_SERVICE_POINT": ["customer_id", "service_point_id"],
        "OUTAGE_CIRCUIT_MAP": ["outage_id", "circuit_id", "transformer_id"],
        "OUTAGE_CUSTOMER_MAP": ["outage_id", "customer_id"],
    }

    ORDERED_SHEETS = [
        "CUSTOMER_TYPE",
        "CHANNEL_MASTER",
        "CUSTOMER",
        "SERVICE_POINT",
        "OUTAGE_EVENT",
        "CUSTOMER_SERVICE_POINT",
        "OUTAGE_CIRCUIT_MAP",
        "OUTAGE_CUSTOMER_MAP",
    ]

    # Wipe order is child-first so foreign keys are respected on databases that
    # enforce them. raw_outage_event is cleared last (audit log); the current import
    # writes a fresh one afterwards.
    RESET_DELETION_ORDER = [
        NotificationAttempt,
        Notification,
        OutageCustomerMap,
        OutageCircuitMap,
        CustomerServicePoint,
        OutageEvent,
        ServicePoint,
        Customer,
        ChannelMaster,
        CustomerType,
        RawOutageEvent,
    ]

    def __init__(
        self,
        db: Session,
        *,
        rebase_times: bool | None = None,
        reset_on_upload: bool | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        # When None, fall back to the global setting. The upload endpoint can pass an
        # explicit per-request override (test_mode / reset).
        self.rebase_times = self.settings.dev_rebase_times if rebase_times is None else rebase_times
        self.reset_on_upload = (
            self.settings.dev_reset_on_upload if reset_on_upload is None else reset_on_upload
        )

    def import_upload(self, file_name: str, content: bytes) -> dict[str, Any]:
        """Import an uploaded Excel/CSV file and return imported row counts."""
        suffix = Path(file_name).suffix.lower()

        if suffix not in {".xlsx", ".xls", ".csv"}:
            raise AppException(
                "Only .xlsx, .xls, and .csv files are supported",
                400,
                "UNSUPPORTED_FILE_TYPE",
            )

        try:
            logger.info(
                "Starting outage data import",
                extra={"ctx_file_name": file_name, "ctx_file_type": suffix},
            )

            if self.reset_on_upload:
                self._reset_existing_data()

            if suffix in {".xlsx", ".xls"}:
                result = self._import_excel(content, file_name)
            else:
                result = self._import_csv(content, file_name)

            self.db.commit()

            logger.info(
                "Outage data import committed successfully",
                extra={"ctx_file_name": file_name},
            )

            return result

        except AppException:
            self.db.rollback()
            logger.exception(
                "Outage data import failed due to validation error",
                extra={"ctx_file_name": file_name},
            )
            raise

        except Exception as exc:
            self.db.rollback()
            logger.exception(
                "Outage data import failed due to unexpected error",
                extra={"ctx_file_name": file_name},
            )
            raise AppException(
                "Failed to import outage data",
                500,
                "FILE_IMPORT_FAILED",
                {"error": str(exc)},
            ) from exc

    def _import_excel(self, content: bytes, original_file_name: str) -> dict[str, Any]:
        """Import Excel workbook from uploaded bytes."""
        sheets = pd.read_excel(BytesIO(content), sheet_name=None)

        imported: dict[str, int] = {}
        skipped: list[str] = []

        for sheet_name in self.ORDERED_SHEETS:
            df = sheets.get(sheet_name)
            if df is None:
                skipped.append(sheet_name)
                continue
            if sheet_name == "OUTAGE_EVENT" and self.rebase_times:
                df = self._rebase_outage_dataframe(df)
                sheets[sheet_name] = df
            imported[sheet_name] = self._upsert_sheet(sheet_name, df)

        for sheet_name in sheets.keys():
            if sheet_name not in self.MODEL_BY_SHEET:
                skipped.append(sheet_name)

        rebased_file = self._save_rebased_workbook(sheets, original_file_name) if self.rebase_times else None

        self.db.add(
            RawOutageEvent(
                source="excel_upload",
                event_type="workbook_import",
                external_event_id=original_file_name,
                payload={
                    "imported_tables": imported,
                    "skipped_sheets": skipped,
                },
            )
        )

        logger.info(
            "Excel outage data imported",
            extra={
                "ctx_file_name": original_file_name,
                "ctx_imported_tables": imported,
                "ctx_skipped_sheets": skipped,
            },
        )

        return {
            "file_name": original_file_name,
            "imported_tables": imported,
            "skipped_sheets": skipped,
            "rebased_file": rebased_file,
        }

    def _import_csv(self, content: bytes, original_file_name: str) -> dict[str, Any]:
        """Import CSV planned outage rows into OUTAGE_EVENT table for Phase 1."""
        df = pd.read_csv(BytesIO(content))

        required_columns = {
            "outage_id",
            "outage_type",
            "status",
            "start_time",
            "estimated_end_time",
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise AppException(
                "CSV missing required planned outage columns",
                400,
                "INVALID_CSV",
                {"missing": sorted(missing_columns)},
            )

        if self.rebase_times:
            df = self._rebase_outage_dataframe(df)

        imported = self._upsert_sheet("OUTAGE_EVENT", df)

        rebased_file = (
            self._save_rebased_workbook({"OUTAGE_EVENT": df}, original_file_name)
            if self.rebase_times
            else None
        )

        self.db.add(
            RawOutageEvent(
                source="csv_upload",
                event_type="planned_outage_csv_import",
                external_event_id=original_file_name,
                payload={"rows": imported},
            )
        )

        logger.info(
            "CSV outage data imported",
            extra={
                "ctx_file_name": original_file_name,
                "ctx_rows": imported,
            },
        )

        return {
            "file_name": original_file_name,
            "imported_tables": {"OUTAGE_EVENT": imported},
            "skipped_sheets": [],
            "rebased_file": rebased_file,
        }

    def _upsert_sheet(self, sheet_name: str, df: pd.DataFrame) -> int:
        """Upsert a dataframe into the mapped SQLite table."""
        model = self.MODEL_BY_SHEET.get(sheet_name)

        if model is None:
            raise AppException(
                f"Unsupported sheet name: {sheet_name}",
                400,
                "UNSUPPORTED_SHEET",
            )

        keys = self.PRIMARY_KEYS[sheet_name]
        records = self._clean_records(df, model, required_columns=keys, sheet_name=sheet_name)

        if not records:
            logger.warning("Skipping empty sheet", extra={"ctx_sheet_name": sheet_name})
            return 0

        table = model.__table__

        stmt = insert(table).values(records)

        update_columns = {
            column.name: stmt.excluded[column.name]
            for column in table.columns
            if column.name not in keys and column.name in records[0]
        }

        if update_columns:
            stmt = stmt.on_conflict_do_update(index_elements=keys, set_=update_columns)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=keys)

        self.db.execute(stmt)

        logger.info(
            "Sheet upsert completed",
            extra={"ctx_sheet_name": sheet_name, "ctx_row_count": len(records)},
        )

        return len(records)

    def _reset_existing_data(self) -> None:
        """Delete all existing data so the upload fully replaces it (not merges).

        Rows are removed child-first to respect foreign keys. This also clears prior
        notifications, so a re-uploaded scenario starts a clean lifecycle instead of
        being blocked by 'already sent' history. Runs inside the import transaction,
        so a later failure rolls the wipe back too.
        """
        deleted: dict[str, int] = {}
        for model in self.RESET_DELETION_ORDER:
            deleted[model.__tablename__] = self.db.query(model).delete(synchronize_session=False)

        logger.info("Reset existing data before import", extra={"ctx_deleted": deleted})

    def _rebase_outage_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rewrite outage lifecycle times to "now + offset" (IST) for easy testing.

        Testers otherwise have to hand-edit start/estimated/actual end times in the
        source file before every run so notifications fall due. With rebasing on, the
        uploaded times are ignored and replaced relative to the moment of import:
        start = now+3m, estimated_end = now+5m, actual_end = now+8m (offsets configurable).
        Each time column is rebased independently and only where the source cell
        already holds a value: a blank cell stays blank (e.g. an outage with no
        actual_end_time is left "not yet restored"). Columns missing from the file are
        not created. Cancellation flags and status are left untouched. Returns a new
        DataFrame so the caller can both upsert and export the rebased values.
        """
        base = ist_now()
        offsets = {
            "start_time": base + timedelta(minutes=self.settings.rebase_start_offset_min),
            "estimated_end_time": base + timedelta(minutes=self.settings.rebase_estimated_end_offset_min),
            "actual_end_time": base + timedelta(minutes=self.settings.rebase_actual_end_offset_min),
        }

        df = df.copy()
        rebased_counts: dict[str, int] = {}
        for column, value in offsets.items():
            if column not in df.columns:
                continue
            # Source columns may be read as string/str dtype; cast to object so the
            # datetime values can be assigned without a dtype conflict.
            df[column] = df[column].astype(object)
            # Per-column mask: only cells that already hold a value are updated;
            # blank cells stay blank.
            col_mask = df[column].notna()
            df.loc[col_mask, column] = value
            rebased_counts[column] = int(col_mask.sum())

        logger.info(
            "Rebased outage times to current IST for testing",
            extra={"ctx_rebased_counts": rebased_counts, "ctx_base_now": base.isoformat()},
        )
        return df

    def _save_rebased_workbook(self, sheets: dict[str, pd.DataFrame], original_file_name: str) -> str:
        """Persist the rebased data to an .xlsx so testers keep a copy of what was imported.

        Excel uploads keep every original sheet (only OUTAGE_EVENT times changed); CSV
        uploads produce a single OUTAGE_EVENT sheet. The file is overwritten on each
        upload so it always reflects the latest import.
        """
        output_dir = BACKEND_DIR / "sample_data" / "rebased"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{Path(original_file_name).stem}_rebased.xlsx"

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)

        logger.info(
            "Saved rebased workbook for testing",
            extra={"ctx_output_path": str(output_path), "ctx_sheets": list(sheets.keys())},
        )
        return str(output_path)

    def _clean_records(
        self,
        df: pd.DataFrame,
        model: type,
        *,
        required_columns: list[str],
        sheet_name: str,
    ) -> list[dict[str, Any]]:
        """Normalize pandas dataframe rows before database insert."""
        records: list[dict[str, Any]] = []
        datetime_columns = {
            column.name
            for column in model.__table__.columns
            if isinstance(column.type, DateTime)
        }

        for row_number, raw in enumerate(df.to_dict(orient="records"), start=2):
            row = {}
            for key, value in raw.items():
                if key is None:
                    continue
                column = str(key).strip()
                if not column:
                    continue
                if pd.isna(value):
                    row[column] = None
                else:
                    row[column] = normalize_value(value, is_datetime=column in datetime_columns)

            if not row or all(value is None for value in row.values()):
                continue

            missing_required = [column for column in required_columns if row.get(column) is None]
            if missing_required:
                raise AppException(
                    "Import row missing required primary key values",
                    400,
                    "INVALID_IMPORT_ROW",
                    {
                        "sheet": sheet_name,
                        "row_number": row_number,
                        "missing": missing_required,
                    },
                )

            records.append(row)

        return records


def normalize_value(value: Any, *, is_datetime: bool = False) -> Any:
    """Normalize Excel/CSV cell values for database insert."""
    if is_datetime:
        return normalize_datetime(value)

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() == "true":
            return True
        if stripped.lower() == "false":
            return False
        if stripped == "":
            return None
        return stripped
    return value


def normalize_datetime(value: Any) -> datetime | date | None:
    """Convert pandas/Excel/CSV datetime values into Python objects SQLite accepts."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, datetime | date):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        parsed = pd.to_datetime(stripped, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()

    return value
