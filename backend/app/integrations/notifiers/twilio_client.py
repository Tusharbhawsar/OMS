"""Shared Twilio REST helpers.

We call Twilio's HTTP API directly with `requests` (already a project dependency)
instead of the `twilio` SDK. The SDK pulls in aiohttp/frozenlist for its async client,
which can't be installed behind the corporate proxy — and we only need the simple
synchronous REST calls anyway (HTTP Basic Auth + form-encoded POST).

All three adapters (SMS, WhatsApp, Voice/IVR) share:
  * twilio_post()          -> makes the authenticated POST to a Twilio resource
  * result_from_response() -> normalizes Twilio's JSON response into a DeliveryResult
"""

from pathlib import Path

import requests

from app.core.config import BACKEND_DIR, get_settings
from app.integrations.notifiers.base import DeliveryResult

# Base URL for Twilio's classic REST API (Messages, Calls, etc.).
TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

# Network timeout (seconds) so a stuck request never hangs a notification batch.
_TIMEOUT = 15


def _verify_arg() -> str | bool:
    """Resolve the `verify` argument for requests.

    Returns a path to a custom CA bundle when SSL_CA_BUNDLE is set (needed behind a
    corporate TLS-inspection proxy), otherwise True to use the default certifi bundle.
    A relative path is resolved against the backend directory.
    """
    bundle = get_settings().ssl_ca_bundle.strip()
    if not bundle:
        return True
    path = Path(bundle)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return str(path)


def twilio_post(resource: str, data: dict[str, str]) -> requests.Response:
    """POST form data to a Twilio account resource (e.g. "Messages", "Calls").

    Auth is HTTP Basic with (Account SID, Auth Token) — exactly what the SDK does
    under the hood. Callers guard on settings.twilio_account_sid before calling.
    """
    settings = get_settings()
    url = f"{TWILIO_API_BASE}/Accounts/{settings.twilio_account_sid}/{resource}.json"
    return requests.post(
        url,
        data=data,
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=_TIMEOUT,
        verify=_verify_arg(),
    )


def result_from_response(provider_name: str, resp: requests.Response, accepted_statuses: set[str]) -> DeliveryResult:
    """Turn a Twilio Messages/Calls JSON response into a normalized DeliveryResult.

    Twilio returns 2xx with a JSON body containing `sid` and `status` on success, or
    a 4xx with a JSON `message` on error. We map its status vocabulary onto our
    Delivered/Failed model; "accepted" states (queued/sent/…) count as Delivered
    because final delivery confirmation only arrives later via a status webhook.
    """
    try:
        body = resp.json()
    except ValueError:
        body = {}

    # HTTP error (bad number, unverified trial recipient, auth failure, etc.).
    if resp.status_code >= 400:
        message = body.get("message") or f"HTTP {resp.status_code}"
        return DeliveryResult(provider_name, "Failed", error_message=message)

    status = str(body.get("status", ""))
    normalized = "Delivered" if status in accepted_statuses else "Failed"
    return DeliveryResult(
        provider_name,
        normalized,
        provider_message_id=body.get("sid"),
        error_message=None if normalized == "Delivered" else f"Twilio status: {status}",
    )
