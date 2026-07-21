import logging

from fastapi import FastAPI
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI, engine: Engine) -> None:
    """Monitoring stack removed for this; keep call site stable."""
    _ = app
    _ = engine
    logger.info("Telemetry setup skipped (monitoring stack disabled)")
