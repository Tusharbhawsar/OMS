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

    database_url: str = Field(default="postgresql+psycopg2://postgres:root@localhost:5432/outage_poc", alias="DATABASE_URL")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")

    notification_mode: Literal["sandbox", "provider"] = Field(default="sandbox", alias="NOTIFICATION_MODE")
    sandbox_email_from: str = Field(default="no-reply@outage-poc.local", alias="SANDBOX_EMAIL_FROM")
    sandbox_sms_from: str = Field(default="+15550000000", alias="SANDBOX_SMS_FROM")

    # Default country code prepended to bare national phone numbers (e.g. a stored
    # "8208382505" becomes "+918208382505") so SMS/WhatsApp/IVR destinations are valid
    # E.164 for Twilio. Numbers already in +<country> form are left untouched.
    default_country_code: str = Field(default="+91", alias="DEFAULT_COUNTRY_CODE")

    email_backend: Literal["smtp", "sandbox"] = Field(default="sandbox", alias="EMAIL_BACKEND")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="no-reply@outage-poc.local", alias="SMTP_FROM_EMAIL")
    smtp_tls: bool = Field(default=True, alias="SMTP_TLS")

    # Twilio settings for REAL SMS / WhatsApp / Voice(IVR) delivery. These are used only
    # when NOTIFICATION_MODE=provider; in the default "sandbox" mode the messages are just
    # logged. Email is deliberately NOT routed through Twilio (Twilio has no email product) —
    # it stays on EMAIL_BACKEND (smtp/sandbox) above.
    #
    # Fail-safe by design: if twilio_account_sid is blank, each Twilio notifier returns a
    # "Failed" DeliveryResult WITHOUT making a network call — mirroring the SMTP adapter's
    # "SMTP_HOST not configured" guard. So a half-configured provider never crashes a run.
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    # E.164 sender for SMS, e.g. +12025550123 (your Twilio trial number).
    twilio_sms_from: str = Field(default="", alias="TWILIO_SMS_FROM")
    # WhatsApp sender. On a trial this is Twilio's shared sandbox number.
    twilio_whatsapp_from: str = Field(default="whatsapp:+14155238886", alias="TWILIO_WHATSAPP_FROM")
    # E.164 caller ID for outbound IVR voice calls (your Twilio trial number).
    twilio_voice_from: str = Field(default="", alias="TWILIO_VOICE_FROM")
    # Text-to-speech language/voice locale used by the IVR <Say> verb.
    twilio_voice_language: str = Field(default="en-US", alias="TWILIO_VOICE_LANGUAGE")

    # Corporate TLS-inspection proxies re-sign HTTPS traffic with an internal root CA
    # that Python's default (certifi) bundle does not trust, causing
    # CERTIFICATE_VERIFY_FAILED on outbound calls (e.g. to api.twilio.com). Point this
    # at a PEM bundle that includes that CA (e.g. exported from the Windows root store).
    # A relative path is resolved against the backend directory. Blank = use the default
    # certifi bundle (correct on networks without TLS interception).
    ssl_ca_bundle: str = Field(default="", alias="SSL_CA_BUNDLE")

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
