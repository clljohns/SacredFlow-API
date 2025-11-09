# ================================================================
# File: square.py
# Path: app/routes/square.py
# Description: Handles Square webhook payloads for SacredFlow integrations.
# Author: SacredFlow Engineering
# ================================================================

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.square import SquareConfigurationError, verify_square_signature
from app.models.payments import Payment
from app.models.webhook import SquareWebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter()


def _square_status_to_internal(status_value: Optional[str]) -> str:
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
    normalized = (status_value or "").upper()
    return mapping.get(normalized, Payment.STATUS_PENDING)


async def _apply_payment_update(payment_payload: Dict[str, Any], session: AsyncSession) -> str:
    square_payment_id = payment_payload.get("id")
    if not square_payment_id:
        logger.warning("Payment webhook missing Square payment id")
        return "ignored"

    result = await session.execute(
        select(Payment).where(Payment.square_payment_id == square_payment_id)
    )
    payment: Optional[Payment] = result.scalar_one_or_none()
    if not payment:
        logger.info("Received Square event for unknown payment %s", square_payment_id)
        return "ignored"

    payment.status = _square_status_to_internal(payment_payload.get("status"))
    extra = dict(payment.extra_data or {})
    history = extra.setdefault("webhook_history", [])
    history.append({
        "received_at": datetime.now(tz=UTC).isoformat(),
        "payload": payment_payload,
    })
    extra["square_response"] = payment_payload
    payment.extra_data = extra
    return "processed"


async def _dispatch_event(payload: Dict[str, Any], session: AsyncSession) -> str:
    event_type = payload.get("type", "unknown")
    data = payload.get("data", {})
    resource = data.get("object", {})

    if event_type.startswith("payment."):
        payment_payload = resource.get("payment") or resource
        return await _apply_payment_update(payment_payload, session)

    logger.info("No handler for Square event type %s", event_type)
    return "ignored"


@router.post("/square/webhook", tags=["square"], status_code=status.HTTP_202_ACCEPTED)
async def handle_square_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_square_signature: Optional[str] = Header(default=None, alias="x-square-signature"),
):
    raw_body = await request.body()

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Invalid Square webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body") from exc

    event_id = payload.get("event_id") or payload.get("eventId")
    if not event_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing event_id")

    signature_valid = True
    try:
        signature_valid = verify_square_signature(raw_body, str(request.url), x_square_signature)
    except SquareConfigurationError as exc:
        logger.warning("Square configuration error during signature verification: %s", exc)

    result = await session.execute(
        select(SquareWebhookEvent).where(SquareWebhookEvent.event_id == event_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("Ignoring duplicate Square webhook %s", event_id)
        return {"status": existing.status, "duplicate": True}

    event_record = SquareWebhookEvent(
        event_id=event_id,
        event_type=payload.get("type", "unknown"),
        location_id=(payload.get("data") or {}).get("location_id"),
        signature_verified=signature_valid,
        payload=payload,
        status="received",
    )
    session.add(event_record)

    processing_status = "ignored"
    failure_reason: Optional[str] = None

    if not signature_valid:
        processing_status = "rejected"
        failure_reason = "Signature verification failed"
    else:
        try:
            processing_status = await _dispatch_event(payload, session)
        except Exception as exc:  # noqa: BLE001 - safe-guard webhook pipeline
            logger.exception("Square webhook processing failed")
            processing_status = "failed"
            failure_reason = str(exc)

    event_record.status = processing_status
    event_record.failure_reason = failure_reason
    if processing_status in {"processed", "ignored"}:
        event_record.processed_at = datetime.now(tz=UTC)

    await session.commit()

    return {
        "status": processing_status,
        "eventId": event_id,
        "signatureVerified": signature_valid,
        "failureReason": failure_reason,
    }
