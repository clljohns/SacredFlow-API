# ================================================================
# File: payments.py
# Path: app/routes/payments.py
# Description: Square payment processing and webhook endpoints.
# Works with squareup v43.2.0.20251016 (typed Payment objects)
# ================================================================

from fastapi import APIRouter, HTTPException
from app.core.config import settings
from square.client import Square
from square.environment import SquareEnvironment
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

# ---------------------------------------------------------------
# 🧩 Environment Resolution
# ---------------------------------------------------------------
def _resolve_square_environment(value: str | None) -> SquareEnvironment:
    """Normalize environment string for Square SDK."""
    if not value:
        return SquareEnvironment.SANDBOX
    value = value.strip().upper()
    if value in {"PRODUCTION", "PROD", "LIVE"}:
        return SquareEnvironment.PRODUCTION
    return SquareEnvironment.SANDBOX


# ---------------------------------------------------------------
# 💳 Initialize Square client
# ---------------------------------------------------------------
square = Square(
    token=settings.SQUARE_SECRET_KEY,  # ✅ correct for squareup 43.x
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
        pager = square.payments.list(limit=10)
        payments = []

        for item in pager:
            # item may be a dict or a typed Payment model
            if isinstance(item, dict):
                payments.extend(item.get("payments", []))
            elif hasattr(item, "payments"):
                # typed response object — convert to dict
                payments.extend([
                    p.to_dict() if hasattr(p, "to_dict") else vars(p)
                    for p in getattr(item, "payments", [])
                ])
            elif hasattr(item, "to_dict"):
                # single object fallback
                payments.append(item.to_dict())
            else:
                payments.append(vars(item))

            if len(payments) >= 10:
                break

        return payments[:10]

    except Exception as e:
        logger.exception("Error fetching Square payments.")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------
# 💫 Webhook Handler
# ---------------------------------------------------------------
@router.post("/webhook", summary="Handle Square Webhook Events")
async def handle_webhook(payload: dict):
    """Handle webhook notifications from Square (e.g., payment updates)."""
    event_type = payload.get("type", "unknown")
    logger.info(f"🔔 Received Square Webhook: {event_type}")
    return {"status": "ok", "received_event": event_type}
