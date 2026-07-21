import json
import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _coerce(value: Any, caster: type) -> Any | None:
    """Best-effort cast of a generation param from auth.json; None if unusable."""
    if value is None:
        return None
    try:
        return caster(value)
    except (TypeError, ValueError):
        return None


class GeminiClient:
    """Thin wrapper around Gemini on Vertex AI for generating notification text.

    Auth uses the service-account JSON at settings.gemini_credentials_path. That same
    file also carries the generation params (TEMPERATURE, MAX_OUTPUT_TOKENS, TOP_P,
    TOP_K, CANDIDATE_COUNT) which are fed into GenerateContentConfig.

    The client is intentionally fail-soft: if the SDK is missing or init fails,
    `available` stays False and callers fall back to deterministic templates so
    notifications are never blocked by an LLM problem.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._gen_params: dict[str, Any] = {}
        self._init()

    def _init(self) -> None:
        if not self.settings.llm_enabled:
            logger.info("LLM disabled via settings; using template messages only.")
            return
        try:
            from google import genai  # noqa: PLC0415
            from google.oauth2 import service_account  # noqa: PLC0415

            with open(self.settings.gemini_credentials_path, encoding="utf-8") as fh:
                creds_data = json.load(fh)

            credentials = service_account.Credentials.from_service_account_info(
                creds_data,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self._client = genai.Client(
                vertexai=True,
                project=creds_data["project_id"],
                location=self.settings.gemini_location,
                credentials=credentials,
            )
            self._gen_params = {
                "temperature": _coerce(creds_data.get("TEMPERATURE"), float),
                "max_output_tokens": _coerce(creds_data.get("MAX_OUTPUT_TOKENS"), int),
                "top_p": _coerce(creds_data.get("TOP_P"), float),
                "top_k": _coerce(creds_data.get("TOP_K"), int),
                "candidate_count": _coerce(creds_data.get("CANDIDATE_COUNT"), int),
            }
            logger.info(
                "Gemini client ready (project=%s, location=%s, model=%s)",
                creds_data.get("project_id"),
                self.settings.gemini_location,
                self.settings.gemini_model,
            )
        except Exception:  # noqa: BLE001 - any failure must degrade to templates, not crash.
            self._client = None
            logger.exception("Gemini client init failed; falling back to template messages.")

    @property
    def available(self) -> bool:
        return self._client is not None

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate text from Gemini. Raises on failure so the caller can fall back.

        `temperature`, when provided, overrides the auth.json default for this call
        (factual notification text needs a low temperature for fact fidelity).
        """
        if self._client is None:
            raise RuntimeError("Gemini client is not available")

        from google.genai import types  # noqa: PLC0415

        config_kwargs = {key: value for key, value in self._gen_params.items() if value is not None}
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        response = self._client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return (response.text or "").strip()


@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    """Return a process-wide singleton Gemini client (credentials loaded once)."""
    return GeminiClient()
