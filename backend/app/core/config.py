from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

_settings_cache: "Settings | None" = None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="outage-poc-backend", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    database_url: str = Field(default="postgresql+psycopg2://postgres:8888@localhost:5432/outage_poc", alias="DATABASE_URL")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")

    notification_mode: Literal["sandbox", "provider"] = Field(default="sandbox", alias="NOTIFICATION_MODE")
    sandbox_email_from: str = Field(default="no-reply@outage-poc.local", alias="SANDBOX_EMAIL_FROM")
    sandbox_sms_from: str = Field(default="+15550000000", alias="SANDBOX_SMS_FROM")

    email_backend: Literal["smtp", "sandbox"] = Field(default="sandbox", alias="EMAIL_BACKEND")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="no-reply@outage-poc.local", alias="SMTP_FROM_EMAIL")
    smtp_tls: bool = Field(default=True, alias="SMTP_TLS")

    # LLM (Gemini via Vertex AI) settings for smart/multilingual notification messages.
    # llm_enabled gates the whole feature: when off (or when a call fails), the
    # deterministic MessageTemplateService is used so notifications never break.
    llm_enabled: bool = Field(default=True, alias="LLM_ENABLED")
    gemini_credentials_path: str = Field(
        default=str(BACKEND_DIR / "auth.json"), alias="GEMINI_CREDENTIALS_PATH"
    )
    # gemini-2.5-flash is what this Vertex project has access to (2.0-flash returns 404
    # for the gen-lang-client project). Override via GEMINI_MODEL if access changes.
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_location: str = Field(default="us-central1", alias="GEMINI_LOCATION")
    # Fallback language used when a customer has no preferred_language set.
    default_language: str = Field(default="en", alias="DEFAULT_LANGUAGE")

    batch_scheduler_enabled: bool = Field(default=False, alias="BATCH_SCHEDULER_ENABLED")
    # batch_interval_minutes: int = Field(default=5, alias="BATCH_INTERVAL_MINUTES")
    batch_interval_minutes: float = Field(default=5, alias="BATCH_INTERVAL_MINUTES")

    # Testing helper: rebase uploaded outage times to "now + offset" (in IST) at import
    # time, so testers don't have to hand-edit start/end times in the Excel/CSV before
    # every run. OFF by default so real uploads are never silently mutated.
    dev_rebase_times: bool = Field(default=False, alias="DEV_REBASE_TIMES")
    rebase_start_offset_min: float = Field(default=3, alias="REBASE_START_OFFSET_MIN")
    rebase_estimated_end_offset_min: float = Field(default=5, alias="REBASE_ESTIMATED_END_OFFSET_MIN")
    rebase_actual_end_offset_min: float = Field(default=8, alias="REBASE_ACTUAL_END_OFFSET_MIN")

    # Testing helper: wipe all existing data before an upload so the new file
    # fully replaces it instead of merging (upsert). Also clears prior notifications,
    # so a re-uploaded scenario runs a clean lifecycle. OFF by default (destructive).
    dev_reset_on_upload: bool = Field(default=False, alias="DEV_RESET_ON_UPLOAD")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        """Accept common deployment-mode values if DEBUG leaks from the shell."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value


def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings()  # type: ignore[call-arg]
    return _settings_cache
