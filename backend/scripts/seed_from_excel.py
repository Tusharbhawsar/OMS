from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.logging import setup_logging
from app.core.database import SessionLocal
from app.services.file_ingestion_service import FileIngestionService


def main() -> None:
    setup_logging()

    path = BASE_DIR / "sample_data" / "data_outage_system.xlsx"

    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")

    db = SessionLocal()
    try:
        result = FileIngestionService(db).import_upload(path.name, path.read_bytes())
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()