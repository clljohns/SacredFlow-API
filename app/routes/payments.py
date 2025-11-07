# ================================================================
# File: payments.py
# Path: app/routes/payments.py
# Description: Square payment processing and webhook endpoints.
# Works with squareup v38.x+ (Client / PaymentsApi)
# ================================================================

import logging

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from square.client import Client
from square.http.auth.o_auth_2 import BearerAuthCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

# ---------------------------------------------------------------
# 🧩 Environment Resolution
# ---------------------------------------------------------------
def _resolve_square_environment(value: str | None) -> str:
    """Normalize environment string for Square SDK."""
    if not value:
        return "sandbox"
    value = value.strip().upper()
    if value in {"PRODUCTION", "PROD", "LIVE"}:
        return "production"
    return "sandbox"


# ---------------------------------------------------------------
# 💳 Initialize Square client
# ---------------------------------------------------------------
square = Client(
    bearer_auth_credentials=BearerAuthCredentials(settings.SQUARE_SECRET_KEY),
    environment=_resolve_square_environment(settings.SQUARE_ENVIRONMENT),
)

# ---------------------------------------------------------------
# 💰 List Payments (Typed Response Compatible)
# ---------------------------------------------------------------
@router.get("/", summary="List Square Payments")
async def list_payments():
    """
    Retrieve up to 10 recent payments from Square (sandbox or production).
    Handles both dict and typed-object responses depending on SDK version.
    """
    try:
        result = square.payments.list_payments(limit=10)
        if result.is_success():
            body = result.body or {}
            return body.get("payments", [])
        error_payload = result.errors if result else []
        logger.error("Square API error when listing payments: %s", error_payload)
        raise HTTPException(status_code=502, detail="Failed to retrieve payments from Square.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error fetching Square payments.")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------
# 💫 Webhook Handler
# ---------------------------------------------------------------
@router.post("/webhook", summary="Handle Square Webhook Events")
async def handle_webhook(payload: dict):
    """Handle webhook notifications from Square (e.g., payment updates)."""
    event_type = payload.get("type", "unknown")
    logger.info(f"🔔 Received Square Webhook: {event_type}")
    return {"status": "ok", "received_event": event_type}
