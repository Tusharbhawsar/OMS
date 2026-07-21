from pydantic import BaseModel


class UploadResult(BaseModel):
    file_name: str
    imported_tables: dict[str, int]
    skipped_sheets: list[str]
