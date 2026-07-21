from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""

    status_code: int = Field(..., examples=[200])
    message: str = Field(..., examples=["Request completed successfully"])
    data: T | None = None


def success_response(status_code: int, message: str, data: Any = None) -> dict[str, Any]:
    """Return a consistent success response dictionary."""
    return {"status_code": status_code, "message": message, "data": data}
