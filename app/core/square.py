# ================================================================
# File: square.py
# Path: app/core/square.py
# Description: Square platform utilities including client creation,
#              health checks, and webhook signature validation.
# Author: SacredFlow Engineering
# ================================================================

from __future__ import annotations

import asyncio
import base64
import hmac
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha1
from pathlib import Path
from typing import Optional

from square.client import Client
from square.http.auth.o_auth_2 import BearerAuthCredentials
from square.http.http_client import RequestsClient
from square.http.http_client_configuration import HttpClientConfiguration
from square.http.response import Response

from app.core.config import settings

logger = logging.getLogger(__name__)


class SquareConfigurationError(RuntimeError):
    """Raised when Square secrets or configuration are missing."""


@dataclass(slots=True, frozen=True)
class SquareRuntimeConfig:
    """Runtime representation of Square credentials and client options."""

    access_token: str
    environment: str
    webhook_signature_key: str | None
    request_timeout: float
    max_retries: int


def _read_secret(value: str, file_env_var: str) -> str:
    """Read a sensitive value either directly or from a file path."""

    file_path = os.getenv(file_env_var, "").strip()
    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise SquareConfigurationError(f"Secret file {file_path} does not exist")

        # Ensure the secret file is not group/world readable for safety.
        try:
            mode = path.stat().st_mode
            if mode & 0o077:
                raise SquareConfigurationError(
                    f"Secret file {file_path} must not be group/world readable"
                )
        except OSError as exc:
            raise SquareConfigurationError(
                f"Unable to inspect permissions for {file_path}: {exc}"
            ) from exc

        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise SquareConfigurationError(
                f"Unable to read secret file {file_path}: {exc}"
            ) from exc
        return content
    return value.strip()


def _resolve_environment(value: str | None) -> str:
    if not value:
        return "sandbox"
    value = value.strip().lower()
    if value in {"production", "prod", "live"}:
        return "production"
    return "sandbox"


@lru_cache
def get_square_runtime_config() -> SquareRuntimeConfig:
    """Build the runtime configuration by combining env variables and secret files."""

    access_token = _read_secret(settings.SQUARE_SECRET_KEY, "SQUARE_SECRET_KEY_FILE")
    if not access_token:
        raise SquareConfigurationError("SQUARE_SECRET_KEY (or file) must be configured")

    webhook_key = _read_secret(
        os.getenv("SQUARE_WEBHOOK_SIGNATURE_KEY", ""),
        "SQUARE_WEBHOOK_SIGNATURE_KEY_FILE",
    )

    timeout = float(os.getenv("SQUARE_HTTP_TIMEOUT", "10"))
    max_retries = int(os.getenv("SQUARE_HTTP_MAX_RETRIES", "3"))

    return SquareRuntimeConfig(
        access_token=access_token,
        environment=_resolve_environment(settings.SQUARE_ENVIRONMENT),
        webhook_signature_key=webhook_key or None,
        request_timeout=timeout,
        max_retries=max_retries,
    )


@lru_cache
def get_square_client() -> Client:
    """Return a configured Square API client with retry/timeout policies."""

    config = get_square_runtime_config()

    http_config = HttpClientConfiguration(
        timeout=config.request_timeout,
        max_retries=config.max_retries,
    )
    http_client = RequestsClient(config=http_config)

    logger.debug(
        "Initializing Square client", environment=config.environment, retries=config.max_retries
    )

    return Client(
        bearer_auth_credentials=BearerAuthCredentials(config.access_token),
        environment=config.environment,
        http_client=http_client,
    )


async def call_square(endpoint: str, func, *args, **kwargs) -> Response:
    """
    Execute a Square SDK call in a thread to avoid blocking the event loop.

    Parameters
    ----------
    endpoint: str
        Name of the Square API endpoint for logging context.
    func: Callable
        Function reference obtained from the Square client.
    *args, **kwargs:
        Positional and keyword arguments forwarded to the SDK call.
    """

    def _invoke():
        return func(*args, **kwargs)

    logger.debug("Invoking Square endpoint", extra={"endpoint": endpoint})
    return await asyncio.to_thread(_invoke)


def verify_square_signature(raw_body: bytes, url: str, provided_signature: str | None) -> bool:
    """Validate webhook signatures using the configured signature key."""

    config = get_square_runtime_config()
    if not config.webhook_signature_key:
        logger.warning("Square webhook signature key not configured; skipping verification")
        return True

    if not provided_signature:
        logger.warning("Missing Square signature header")
        return False

    message = (url + raw_body.decode("utf-8")).encode("utf-8")
    computed = hmac.new(
        config.webhook_signature_key.encode("utf-8"), message, sha1
    ).digest()
    expected_signature = base64.b64encode(computed).decode("utf-8")
    if hmac.compare_digest(expected_signature, provided_signature):
        return True

    logger.error(
        "Square signature verification failed", extra={"expected": expected_signature}
    )
    return False


async def square_healthcheck() -> dict[str, Optional[str]]:
    """Retrieve a lightweight health snapshot from Square."""

    try:
        client = get_square_client()
    except SquareConfigurationError as exc:
        logger.warning("Square configuration unavailable: %s", exc)
        return {
            "status": "degraded",
            "reason": str(exc),
        }

    try:
        response = await call_square(
            "locations.list_locations", client.locations.list_locations
        )
    except Exception as exc:  # noqa: BLE001 - capturing SDK exceptions generically
        logger.exception("Square healthcheck failed")
        return {
            "status": "error",
            "reason": str(exc),
        }

    if response.is_success():
        body = response.body or {}
        locations = body.get("locations", [])
        location_ids = [loc.get("id") for loc in locations if loc.get("id")]
        return {
            "status": "ok",
            "environment": get_square_runtime_config().environment,
            "locations": ",".join(location_ids) if location_ids else None,
        }

    errors = response.errors or []
    logger.error("Square healthcheck returned errors", extra={"errors": errors})
    return {
        "status": "error",
        "reason": "; ".join(err.get("detail", str(err)) for err in errors),
    }


def reset_square_caches() -> None:
    """Utility for tests to reset cached configuration and client instances."""

    get_square_runtime_config.cache_clear()
    get_square_client.cache_clear()

