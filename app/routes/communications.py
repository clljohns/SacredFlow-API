# ================================================================
# File: communications.py
# Path: app/routes/communications.py
# Description: API endpoints for logging and routing SacredFlow communications.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.communication import Communication
from app.schemas.communication import (
    ChatMessageRequest,
    ChatRelayResponse,
    CommunicationCreate,
    CommunicationRead,
    CommunicationUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communications", tags=["Communications"])


async def _create_communication(session: AsyncSession, payload: CommunicationCreate) -> Communication:
    """Persist a communication entry and return the ORM instance."""
    record = Communication(
        channel=payload.channel,
        direction=payload.direction,
        status=payload.status or "queued",
        subject=payload.subject,
        body=payload.body,
        user_id=payload.user_id,
        contact_email=str(payload.contact_email) if payload.contact_email else None,
        contact_name=payload.contact_name,
        external_reference=payload.external_reference,
        meta=dict(payload.meta or {}),
        attachments=list(payload.attachments or []),
        is_read=payload.is_read
        if payload.is_read is not None
        else payload.direction != "inbound",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


def _apply_filters(
    stmt: Select[tuple[Communication]],
    *,
    channel: Optional[str],
    direction: Optional[str],
    is_read: Optional[bool],
    user_id: Optional[str],
) -> Select[tuple[Communication]]:
    if channel:
        stmt = stmt.filter(Communication.channel == channel)
    if direction:
        stmt = stmt.filter(Communication.direction == direction)
    if is_read is not None:
        stmt = stmt.filter(Communication.is_read.is_(is_read))
    if user_id:
        stmt = stmt.filter(Communication.user_id == user_id)
    return stmt


@router.get("", response_model=List[CommunicationRead])
@router.get("/", response_model=List[CommunicationRead])
async def list_communications(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    channel: Optional[str] = Query(default=None),
    direction: Optional[str] = Query(default=None),
    is_read: Optional[bool] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> List[CommunicationRead]:
    stmt = select(Communication).order_by(Communication.created_at.desc())
    stmt = _apply_filters(
        stmt,
        channel=channel,
        direction=direction,
        is_read=is_read,
        user_id=user_id,
    ).offset(offset).limit(limit)
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [CommunicationRead.model_validate(row) for row in records]


@router.get("/unread-count")
@router.get("/unread-count/")
async def unread_count(session: AsyncSession = Depends(get_session)) -> Dict[str, int]:
    stmt = select(func.count()).select_from(Communication).filter(Communication.is_read.is_(False))
    result = await session.execute(stmt)
    return {"count": int(result.scalar_one())}


@router.get("/{communication_id}", response_model=CommunicationRead)
async def get_communication(
    communication_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CommunicationRead:
    record = await session.get(Communication, communication_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication not found.")
    return CommunicationRead.model_validate(record)


@router.post("", response_model=CommunicationRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CommunicationRead, status_code=status.HTTP_201_CREATED)
async def create_communication(
    payload: CommunicationCreate,
    session: AsyncSession = Depends(get_session),
) -> CommunicationRead:
    record = await _create_communication(session, payload)
    return CommunicationRead.model_validate(record)


@router.patch("/{communication_id}", response_model=CommunicationRead)
async def update_communication(
    communication_id: UUID,
    payload: CommunicationUpdate,
    session: AsyncSession = Depends(get_session),
) -> CommunicationRead:
    record = await session.get(Communication, communication_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication not found.")

    if payload.status is not None:
        record.status = payload.status
    if payload.is_read is not None:
        record.is_read = payload.is_read
    if payload.meta is not None:
        record.meta = dict(payload.meta)

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return CommunicationRead.model_validate(record)


@router.post("/chat/intake", response_model=ChatRelayResponse, status_code=status.HTTP_201_CREATED)
async def intake_chat_message(
    payload: ChatMessageRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatRelayResponse:
    """Log inbound chat message and optionally forward to Square/email/mobile channels."""
    meta = {"page": payload.page} if payload.page else {}
    meta.update(payload.metadata or {})

    communication = await _create_communication(
        session,
        CommunicationCreate(
            channel="chat",
            direction="inbound",
            body=payload.message,
            subject=f"Chat from {payload.visitor_email or payload.visitor_name or 'Visitor'}",
            status="received",
            contact_email=payload.visitor_email,
            contact_name=payload.visitor_name,
            meta=meta,
            attachments=[],
            user_id=None,
            external_reference=None,
            is_read=False,
        ),
    )

    forwarded: Dict[str, bool] = {"square": False, "email": False, "mobile": False}
    warnings: List[str] = []

    # Forward to Square webhook if configured/enabled.
    if payload.forward_to_square and settings.SQUARE_CHAT_WEBHOOK_URL:
        headers = {"Content-Type": "application/json"}
        if settings.SQUARE_CHAT_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {settings.SQUARE_CHAT_BEARER_TOKEN}"
        square_payload = {
            "message": payload.message,
            "visitorEmail": payload.visitor_email,
            "visitorName": payload.visitor_name,
            "page": payload.page,
            "meta": meta,
            "communicationId": str(communication.id),
            "createdAt": communication.created_at.isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.SQUARE_CHAT_WEBHOOK_URL,
                    json=square_payload,
                    headers=headers,
                )
            response.raise_for_status()
            forwarded["square"] = True
        except httpx.HTTPError as exc:
            logger.warning("Square chat forwarding failed: %s", exc)
            warnings.append(f"Square forwarding failed: {exc}")

    # Forward to primary email webhook if enabled.
    if payload.forward_to_primary:
        target_email = payload.primary_email or settings.PRIMARY_INBOX_EMAIL
        if target_email and settings.INBOX_FORWARD_WEBHOOK_URL:
            email_payload = {
                "to": target_email,
                "subject": f"SacredFlow chat from {payload.visitor_email or 'Visitor'}",
                "body": payload.message,
                "meta": meta,
                "communicationId": str(communication.id),
                "visitorEmail": payload.visitor_email,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        settings.INBOX_FORWARD_WEBHOOK_URL,
                        json=email_payload,
                    )
                response.raise_for_status()
                forwarded["email"] = True
            except httpx.HTTPError as exc:
                logger.warning("Email forwarding failed: %s", exc)
                warnings.append(f"Email forwarding failed: {exc}")
        elif not target_email:
            warnings.append("Email forwarding skipped: no primary email configured.")
        elif not settings.INBOX_FORWARD_WEBHOOK_URL:
            warnings.append("Email forwarding skipped: INBOX_FORWARD_WEBHOOK_URL not configured.")

    # Forward to mobile webhook if enabled.
    if payload.forward_to_mobile and settings.INBOX_PUSH_WEBHOOK_URL:
        mobile_payload = {
            "message": payload.message,
            "communicationId": str(communication.id),
            "visitorEmail": payload.visitor_email,
            "page": payload.page,
            "meta": meta,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.INBOX_PUSH_WEBHOOK_URL,
                    json=mobile_payload,
                )
            response.raise_for_status()
            forwarded["mobile"] = True
        except httpx.HTTPError as exc:
            logger.warning("Mobile webhook forwarding failed: %s", exc)
            warnings.append(f"Mobile forwarding failed: {exc}")
    elif payload.forward_to_mobile and not settings.INBOX_PUSH_WEBHOOK_URL:
        warnings.append("Mobile forwarding skipped: INBOX_PUSH_WEBHOOK_URL not configured.")

    return ChatRelayResponse(
        communication=CommunicationRead.model_validate(communication),
        forwarded=forwarded,
        warnings=warnings,
    )
