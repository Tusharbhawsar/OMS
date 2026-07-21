import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.jobs.scheduler import PlannedOutageScheduler
from app.web.upload_page import LOGO_DATA_URI, UPLOAD_PAGE_HTML

setup_logging()
settings = get_settings()
logger = logging.getLogger(__name__)
scheduler = PlannedOutageScheduler()


async def lifespan(app: FastAPI):
    """Application lifecycle hook for scheduler startup and shutdown."""
    if settings.batch_scheduler_enabled:
        scheduler.start()
        logger.info("Planned outage scheduler started")
    yield
    if settings.batch_scheduler_enabled:
        scheduler.shutdown()
        logger.info("Planned outage scheduler stopped")


app = FastAPI(
    title="Outage Communication System",
    description="Phase 1 FastAPI backend for planned outage communication.",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},  # Expand all models in Swagger UI
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
# setup_telemetry(app, engine)
app.include_router(api_router, prefix=settings.api_v1_prefix)


async def health_check() -> dict[str, object]:
    """Lightweight liveness endpoint."""
    return {"status_code": 200, "message": "Service is healthy", "data": {"service": settings.app_name}}


app.add_api_route("/health", health_check, methods=["GET"], tags=["System"],include_in_schema=False)  # Hide from OpenAPI docs


async def upload_page() -> HTMLResponse:
    """Serve the branded operator upload page at the backend root.

    {{API_BASE}} is substituted at request time with the configured /api/v1 prefix
    so the page's fetch() calls always target the live API mount point, and
    {{LOGO_SRC}} with a base64 data URI of the Cognizant logo (cog_logo.jpg).
    """
    html = (
        UPLOAD_PAGE_HTML
        .replace("{{API_BASE}}", settings.api_v1_prefix)
        .replace("{{LOGO_SRC}}", LOGO_DATA_URI)
    )
    return HTMLResponse(content=html)


app.add_api_route("/", upload_page, methods=["GET"], include_in_schema=False)  # Branded upload UI
