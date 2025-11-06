# ================================================================
# File: communication.py
# Path: app/models/communication.py
# Description: SQLAlchemy model representing SacredFlow communication events.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models import Base


class Communication(Base):
    """Persistent record for chat/email/SMS conversations flowing through SacredFlow."""

    __tablename__ = "communications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    channel = Column(String(32), nullable=False)  # e.g. email, sms, chat
    direction = Column(String(16), nullable=False)  # inbound | outbound
    status = Column(String(32), nullable=False, default="queued")
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    user_id = Column(String(128), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    external_reference = Column(String(255), nullable=True)
    meta = Column(JSONB, nullable=False, default=dict)
    attachments = Column(JSONB, nullable=False, default=list)
    is_read = Column(Boolean, nullable=False, default=False)

    def mark_read(self) -> None:
        self.is_read = True
        self.updated_at = datetime.utcnow()

