from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class AppException(Exception):
    """Base domain exception converted into the standard API error response."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "APP_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        Exception.__init__(self, message)


def error_payload(status_code: int, message: str, error_code: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a consistent API error response payload."""
    return {
        "status_code": status_code,
        "message": message,
        "error_code": error_code,
        "details": details or {},
    }


async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.status_code, exc.message, exc.error_code, exc.details),
    )


async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            "VALIDATION_ERROR",
            {"errors": exc.errors()},
        ),
    )


async def handle_db_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Database operation failed",
            "DATABASE_ERROR",
            {"reason": str(exc.__class__.__name__)},
        ),
    )


async def handle_unknown_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            "INTERNAL_SERVER_ERROR",
            {"reason": str(exc.__class__.__name__)},
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for application, validation, and DB errors."""
    app.add_exception_handler(AppException, handle_app_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(SQLAlchemyError, handle_db_error)
    app.add_exception_handler(Exception, handle_unknown_error)
