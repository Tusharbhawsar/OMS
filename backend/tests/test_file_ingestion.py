import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.exceptions import AppException
from app.models.outage import OutageCustomerMap
from app.services.file_ingestion_service import FileIngestionService


def test_outage_customer_map_import_skips_blank_excel_rows() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    df = pd.DataFrame(
        [
            {
                "outage_id": "OTG_TEST_001",
                "customer_id": "CUST_TEST_001",
                "notification_flag": True,
                "restored_flag": False,
            },
            {
                "outage_id": None,
                "customer_id": None,
                "notification_flag": None,
                "restored_flag": None,
            },
        ]
    )

    with Session(engine) as db:
        imported = FileIngestionService(db)._upsert_sheet("OUTAGE_CUSTOMER_MAP", df)

        assert imported == 1
        assert db.get(
            OutageCustomerMap,
            {"outage_id": "OTG_TEST_001", "customer_id": "CUST_TEST_001"},
        )


def test_import_rejects_rows_missing_primary_key_values() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    df = pd.DataFrame(
        [
            {
                "outage_id": "OTG_TEST_001",
                "customer_id": None,
                "notification_flag": True,
                "restored_flag": False,
            },
        ]
    )

    with Session(engine) as db:
        try:
            FileIngestionService(db)._upsert_sheet("OUTAGE_CUSTOMER_MAP", df)
        except AppException as exc:
            assert exc.error_code == "INVALID_IMPORT_ROW"
            assert exc.details == {
                "sheet": "OUTAGE_CUSTOMER_MAP",
                "row_number": 2,
                "missing": ["customer_id"],
            }
        else:
            raise AssertionError("Expected AppException")
