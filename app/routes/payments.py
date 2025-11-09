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

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_session
from app.models.payments import Payment
from pydantic import BaseModel, ConfigDict, EmailStr, Field, constr
from requests import RequestException
from app.core.square import (
    SquareConfigurationError,
    call_square,
    get_square_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

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


class PortalPaymentRecord(BaseModel):
    id: str
    display_id: Optional[str] = Field(default=None, alias="displayId")
    square_payment_id: Optional[str] = Field(default=None, alias="squarePaymentId")
    plan_type: str = Field(default="subscription", alias="planType")
    status: str
    total: float = Field(..., description="Total amount in USD")
    paid: float = Field(..., description="Paid amount in USD")
    amount_cents: int = Field(..., alias="amountCents")
    currency: str = "USD"
    channel: Optional[str] = None
    cadence: Optional[str] = None
    customer_email: Optional[EmailStr] = Field(default=None, alias="customerEmail")
    customer_name: Optional[str] = Field(default=None, alias="customerName")
    customer_phone: Optional[str] = Field(default=None, alias="customerPhone")
    shipping_address: Optional[Dict[str, Any]] = Field(default=None, alias="shippingAddress")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    square_response: Dict[str, Any] = Field(default_factory=dict, alias="squareResponse")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class PaymentRecordListResponse(BaseModel):
    items: List[PortalPaymentRecord]
    count: int


VALID_COUNTRY_CODES = {
    "AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT","AZ",
    "BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW","BV","BR",
    "IO","BN","BG","BF","BI","CV","KH","CM","CA","KY","CF","TD","CL","CN","CX","CC",
    "CO","KM","CD","CG","CK","CR","CI","HR","CU","CW","CY","CZ","DK","DJ","DM","DO",
    "EC","EG","SV","GQ","ER","EE","SZ","ET","FK","FO","FJ","FI","FR","GF","PF","TF",
    "GA","GM","GE","DE","GH","GI","GR","GL","GD","GP","GU","GT","GG","GN","GW","GY",
    "HT","HM","VA","HN","HK","HU","IS","IN","ID","IR","IQ","IE","IM","IL","IT","JM",
    "JP","JE","JO","KZ","KE","KI","KP","KR","KW","KG","LA","LV","LB","LS","LR","LY",
    "LI","LT","LU","MO","MG","MW","MY","MV","ML","MT","MH","MQ","MR","MU","YT","MX",
    "FM","MD","MC","MN","ME","MS","MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI",
    "NE","NG","NU","NF","MK","MP","NO","OM","PK","PW","PS","PA","PG","PY","PE","PH",
    "PN","PL","PT","PR","QA","RO","RU","RW","RE","BL","SH","KN","LC","MF","PM","VC",
    "WS","SM","ST","SA","SN","RS","SC","SL","SG","SX","SK","SI","SB","SO","ZA","GS",
    "SS","ES","LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH","TL","TG","TK",
    "TO","TT","TN","TR","TM","TC","TV","UG","UA","AE","GB","US","UM","UY","UZ","VU",
    "VE","VN","VG","VI","WF","EH","YE","ZM","ZW"
}


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
        "country": _normalize_country(address.country),
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


def _normalize_country(code: Optional[str]) -> str:
    if not code:
        return "US"
    upper = code.upper()
    if upper in VALID_COUNTRY_CODES:
        return upper
    return "US"


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("+"):
        digits = digits[1:]
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if digits.startswith("+"):
        return digits
    return "+" + digits


def _shipping_snapshot_from_payload(address: Optional["PaymentAddress"]) -> Optional[Dict[str, Any]]:
    if not address:
        return None
    return {
        "line1": address.line1,
        "line2": address.line2,
        "city": address.city,
        "state": address.state,
        "postalCode": address.postal_code,
        "country": _normalize_country(address.country),
    }


def _square_status_to_internal(status: Optional[str]) -> str:
    mapping = {
        "COMPLETED": Payment.STATUS_COMPLETED,
        "APPROVED": Payment.STATUS_PENDING,
        "AUTHORIZED": Payment.STATUS_PENDING,
        "PENDING": Payment.STATUS_PENDING,
        "FAILED": Payment.STATUS_FAILED,
        "CANCELED": Payment.STATUS_FAILED,
        "CANCELED_BY_CUSTOMER": Payment.STATUS_FAILED,
        "REFUNDED": Payment.STATUS_REFUNDED,
    }
    normalized = (status or "").upper()
    return mapping.get(normalized, Payment.STATUS_PENDING)


def _format_amount_dollars(amount_cents: int) -> float:
    quantized = (Decimal(amount_cents) / Decimal("100")).quantize(Decimal("0.01"))
    return float(quantized)


def _generate_display_id() -> str:
    """Create a friendly order identifier surfaced to the portal."""
    return f"ORD-{datetime.utcnow():%Y%m%d}-{uuid4().hex[:6].upper()}"


async def _upsert_payment_record(
    session: AsyncSession,
    *,
    amount_cents: int,
    payload: PaymentIntentRequest,
    square_payment: Dict[str, Any],
    normalized_phone: Optional[str],
    shipping_snapshot: Optional[Dict[str, Any]],
    metadata_snapshot: Dict[str, str],
) -> Payment:
    square_payment_id = square_payment.get("id")

    existing: Optional[Payment] = None
    if square_payment_id:
        result = await session.execute(
            select(Payment).where(Payment.square_payment_id == square_payment_id)
        )
        existing = result.scalar_one_or_none()

    existing_extra = existing.extra_data if existing and isinstance(existing.extra_data, dict) else {}
    display_id = existing_extra.get("display_id") if isinstance(existing_extra, dict) else None
    if not display_id:
        display_id = _generate_display_id()

    status_value = _square_status_to_internal(square_payment.get("status"))
    snapshot = {
        "metadata": metadata_snapshot,
        "square_response": square_payment,
        "customer_name": payload.customer_name,
        "customer_phone": normalized_phone,
        "shipping_address": shipping_snapshot,
        "channel": metadata_snapshot.get("channel") or "SacredFlow Checkout",
        "cadence": metadata_snapshot.get("cadence"),
        "plan_label": payload.plan_type or metadata_snapshot.get("planType") or "subscription",
        "display_id": display_id,
    }
    snapshot = {key: value for key, value in snapshot.items() if value not in (None, "", {})}

    if existing:
        existing.amount = amount_cents
        existing.customer_email = payload.customer_email or existing.customer_email
        existing.plan_type = payload.plan_type or existing.plan_type
        existing.status = status_value
        merged_extra = dict(existing.extra_data or {})
        merged_extra.update(snapshot)
        existing.extra_data = merged_extra
        record = existing
    else:
        record = Payment(
            square_payment_id=square_payment_id,
            customer_email=payload.customer_email,
            plan_type=payload.plan_type or "subscription",
            amount=amount_cents,
            status=status_value,
            extra_data=snapshot,
        )

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


def _payment_to_portal_record(payment: Payment) -> PortalPaymentRecord:
    extra = payment.extra_data or {}
    metadata = extra.get("metadata") or {}
    customer_name = extra.get("customer_name") or metadata.get("customerName")
    customer_phone = extra.get("customer_phone") or metadata.get("customerPhone")
    shipping_address = extra.get("shipping_address")
    cadence = extra.get("cadence") or metadata.get("cadence")
    channel = extra.get("channel") or metadata.get("channel") or "SacredFlow Checkout"

    amount_cents = int(payment.amount or 0)
    total = _format_amount_dollars(amount_cents)
    paid = total if payment.status == Payment.STATUS_COMPLETED else 0.0

    plan_type = payment.plan_type or extra.get("plan_label") or metadata.get("planType") or "subscription"
    status_map = {
        Payment.STATUS_COMPLETED: "paid",
        Payment.STATUS_PENDING: "pending",
        Payment.STATUS_FAILED: "failed",
        Payment.STATUS_REFUNDED: "refunded",
    }
    status_label = status_map.get(payment.status, payment.status or Payment.STATUS_PENDING)

    return PortalPaymentRecord(
        id=str(payment.id),
        square_payment_id=payment.square_payment_id,
        plan_type=plan_type,
        status=status_label,
        total=total,
        paid=paid,
        amount_cents=amount_cents,
        channel=channel,
        cadence=cadence,
        customer_email=payment.customer_email,
        customer_name=customer_name,
        customer_phone=customer_phone,
        shipping_address=shipping_address,
        metadata=metadata,
        square_response=extra.get("square_response") or {},
        created_at=payment.created_at,
        updated_at=payment.updated_at,
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
        client = get_square_client()
        result = await call_square(
            "payments.list_payments", client.payments.list_payments, limit=10
        )
        if result.is_success():
            body = result.body or {}
            return body.get("payments", [])
        error_payload = result.errors if result else []
        logger.error("Square API error when listing payments: %s", error_payload)
        raise HTTPException(status_code=502, detail="Failed to retrieve payments from Square.")
    except SquareConfigurationError as exc:
        logger.error("Square configuration error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
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
async def create_payment(
    payload: PaymentIntentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Charge a card token coming from the Square Web Payments SDK."""
    amount_cents = int(
        (payload.amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")

    normalized_phone = _normalize_phone(payload.customer_phone)
    shipping_snapshot = _shipping_snapshot_from_payload(payload.customer_address)

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
        "metadata": _sanitize_metadata(payload.metadata),
    }

    if payload.customer_email:
        body["buyer_email_address"] = payload.customer_email
    if normalized_phone:
        body["buyer_phone_number"] = normalized_phone
    if payload.customer_name:
        body["billing_address"] = body.get("billing_address", {})
        body["billing_address"]["first_name"] = payload.customer_name.split(" ", 1)[0]
        if " " in payload.customer_name:
            body["billing_address"]["last_name"] = payload.customer_name.split(" ", 1)[1]
    metadata_payload = body["metadata"]

    if payload.customer_name:
        metadata_payload.setdefault("customerName", payload.customer_name)
    if normalized_phone:
        metadata_payload.setdefault("customerPhone", normalized_phone)
    if payload.customer_email:
        metadata_payload.setdefault("customerEmail", payload.customer_email)

    if payload.customer_address and shipping_snapshot:
        square_address = _to_square_address(payload.customer_address)
        body["billing_address"] = {**square_address, **body.get("billing_address", {})}
        body["shipping_address"] = square_address
        metadata_payload.setdefault(
            "customerAddress",
            json.dumps(shipping_snapshot),
        )

    logger.info("Creating Square payment for plan %s", payload.plan_type or "n/a")
    try:
        client = get_square_client()
        result = await call_square(
            "payments.create_payment", client.payments.create_payment, body
        )
    except SquareConfigurationError as exc:
        logger.error("Square configuration error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RequestException as exc:
        logger.exception("Square create_payment request timed out.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Square did not respond in time. Please retry the payment.",
        ) from exc

    if result.is_success():
        payment = (result.body or {}).get("payment", {})
        try:
            await _upsert_payment_record(
                session=session,
                amount_cents=amount_cents,
                payload=payload,
                square_payment=payment,
                normalized_phone=normalized_phone,
                shipping_snapshot=shipping_snapshot,
                metadata_snapshot=dict(metadata_payload),
            )
        except Exception:
            logger.exception(
                "Persisting payment %s failed, returning success to client anyway.",
                payment.get("id"),
            )
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


@router.get(
    "/records",
    response_model=PaymentRecordListResponse,
    summary="List locally recorded SacredFlow payments",
)
async def list_payment_records(
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    customer_email: Optional[EmailStr] = Query(default=None, alias="customerEmail"),
    session: AsyncSession = Depends(get_session),
) -> PaymentRecordListResponse:
    stmt = (
        select(Payment)
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if customer_email:
        stmt = stmt.where(Payment.customer_email == customer_email)

    result = await session.execute(stmt)
    records = result.scalars().all()
    items = [_payment_to_portal_record(record) for record in records]
    return PaymentRecordListResponse(items=items, count=len(items))


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
