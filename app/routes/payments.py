# ================================================================
# File: payments.py
# Path: app/routes/payments.py
# Description: Square payment processing and webhook endpoints.
# Works with squareup v38.x+ (Client / PaymentsApi)
# ================================================================
# File: payments.py
# Path: app/routes/payments.py
# Description: Square payment processing and webhook endpoints.
# Works with squareup v38.x+ (Client / PaymentsApi)
# ================================================================
from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from pydantic import BaseModel, ConfigDict, EmailStr, Field, constr
from requests import RequestException
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
# 📦 Request / Response Schemas
# ---------------------------------------------------------------
class PaymentIntentRequest(BaseModel):
    token: str = Field(..., description="Square card token (nonce).")
    amount: Decimal = Field(..., gt=0)
    plan_type: Optional[str] = Field(default=None, alias="planType")
    customer_email: Optional[EmailStr] = Field(default=None, alias="customerEmail")
    customer_name: Optional[str] = Field(default=None, alias="customerName")
    customer_phone: Optional[str] = Field(default=None, alias="customerPhone")
    customer_address: Optional["PaymentAddress"] = Field(default=None, alias="customerAddress")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class PaymentIntentResponse(BaseModel):
    square_payment_id: str = Field(..., alias="squarePaymentId")
    status: str
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class PaymentConfirmationRequest(BaseModel):
    square_payment_id: Optional[str] = Field(default=None, alias="squarePaymentId")
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class PaymentAddress(BaseModel):
    line1: str = Field(..., alias="line1", min_length=2)
    line2: Optional[str] = Field(default=None, alias="line2")
    city: str = Field(..., alias="city", min_length=2)
    state: str = Field(..., alias="state", min_length=2)
    postal_code: str = Field(..., alias="postalCode", min_length=3)
    country: constr(min_length=2, max_length=2) = Field(default="US", alias="country")  # type: ignore[valid-type]

    model_config = ConfigDict(populate_by_name=True)


def _to_square_address(address: PaymentAddress) -> Dict[str, str]:
    return {
        "address_line_1": address.line1,
        "address_line_2": address.line2,
        "locality": address.city,
        "administrative_district_level_1": address.state,
        "postal_code": address.postal_code,
        "country": (address.country or "US").upper(),
    }


def _sanitize_metadata(metadata: Dict[str, Any] | None) -> Dict[str, str]:
    sanitized: Dict[str, str] = {}
    if not metadata:
        return sanitized
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = str(value)
        else:
            sanitized[key] = json.dumps(value)
    return sanitized

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


# ---------------------------------------------------------------
# 🪄 Frontend payment helpers
# ---------------------------------------------------------------
@router.post(
    "/create",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Square payment",
)
async def create_payment(payload: PaymentIntentRequest):
    """Charge a card token coming from the Square Web Payments SDK."""
    amount_cents = int(
        (payload.amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")

    body: Dict[str, Any] = {
        "idempotency_key": str(uuid4()),
        "source_id": payload.token,
        "amount_money": {
            "amount": amount_cents,
            "currency": "USD",
        },
        "location_id": settings.SQUARE_LOCATION_ID,
        "note": f"SacredFlow checkout: {payload.plan_type or 'general'}",
        "autocomplete": True,
    }

    if payload.customer_email:
        body["buyer_email_address"] = payload.customer_email
    if payload.customer_phone:
        body["buyer_phone_number"] = payload.customer_phone
    if payload.customer_name:
        body["billing_address"] = body.get("billing_address", {})
        body["billing_address"]["first_name"] = payload.customer_name.split(" ", 1)[0]
        if " " in payload.customer_name:
            body["billing_address"]["last_name"] = payload.customer_name.split(" ", 1)[1]
    body["metadata"] = _sanitize_metadata(payload.metadata)

    if payload.customer_name:
        body["metadata"].setdefault("customerName", payload.customer_name)
    if payload.customer_phone:
        body["metadata"].setdefault("customerPhone", payload.customer_phone)
    if payload.customer_email:
        body["metadata"].setdefault("customerEmail", payload.customer_email)

    if payload.customer_address:
        square_address = _to_square_address(payload.customer_address)
        body["billing_address"] = {**square_address, **body.get("billing_address", {})}
        body["shipping_address"] = square_address
        body["metadata"].setdefault(
            "customerAddress",
            json.dumps(
                {
                    "line1": payload.customer_address.line1,
                    "line2": payload.customer_address.line2,
                    "city": payload.customer_address.city,
                    "state": payload.customer_address.state,
                    "postalCode": payload.customer_address.postal_code,
                    "country": payload.customer_address.country,
                }
            ),
        )

    logger.info("Creating Square payment for plan %s", payload.plan_type or "n/a")
    try:
        result = square.payments.create_payment(body)
    except RequestException as exc:
        logger.exception("Square create_payment request timed out.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Square did not respond in time. Please retry the payment.",
        ) from exc

    if result.is_success():
        payment = (result.body or {}).get("payment", {})
        return PaymentIntentResponse(
            square_payment_id=payment.get("id", ""),
            status=payment.get("status", "UNKNOWN"),
            metadata={
                "planType": payload.plan_type,
                "square_response": payment,
            },
        )

    errors = result.errors if result else []
    logger.error("Square create_payment failed: %s", errors)

    error_categories = {err.get("category") for err in errors if isinstance(err, dict)}
    proxied_status = (
        status.HTTP_502_BAD_GATEWAY
        if error_categories & {"API_ERROR", "AUTHENTICATION_ERROR"}
        else status.HTTP_400_BAD_REQUEST
    )

    primary_message = None
    if errors:
        first_error = errors[0]
        if isinstance(first_error, dict):
            primary_message = (
                first_error.get("detail")
                or first_error.get("message")
                or first_error.get("code")
            )
        else:
            primary_message = str(first_error)

    detail_message = primary_message or "Square rejected the payment request."
    raise HTTPException(
        status_code=proxied_status,
        detail={
            "message": detail_message,
            "errors": errors,
        },
    )


@router.post(
    "/confirm",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Confirm frontend payment",
)
async def confirm_payment(payload: PaymentConfirmationRequest):
    """
    Placeholder endpoint for the funnel to acknowledge a payment.
    In a future iteration we can persist metadata or trigger emails.
    """
    logger.info(
        "Confirming payment %s with status %s",
        payload.square_payment_id,
        payload.status,
    )
    return {
        "square_payment_id": payload.square_payment_id,
        "status": payload.status,
        "metadata": payload.metadata or {},
        "received": True,
    }
