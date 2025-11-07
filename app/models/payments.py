# ================================================================
# File: payments.py
# Path: app/models/payments.py
# Description: SQLAlchemy model tracking SacredFlow Square payments.
# Author: Malu Lani Innovations (Backend Engineering)
# Project: SacredFlow API
# ================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Payment(Base):
    """
    Represents a recorded payment processed through Square
    for SacredFlow subscriptions, bundles, or one-time purchases.
    """

    __tablename__ = "payments"

    # ---------------------------------------------------------------
    # Constants for valid statuses
    # ---------------------------------------------------------------
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    # ---------------------------------------------------------------
    # Primary Identifiers
    # ---------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    square_payment_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=True,
        doc="Square's unique payment identifier (if available)."
    )

    # ---------------------------------------------------------------
    # Customer & Plan Details
    # ---------------------------------------------------------------
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        nullable=True,
        doc="Email address associated with the payment (if provided)."
    )

    plan_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Payment category, e.g., 'subscription', 'bundle', or 'one_time'."
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Payment amount in cents (e.g., $1.00 = 100)."
    )

    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=STATUS_PENDING,
        doc="Current state of the payment record."
    )

    # ---------------------------------------------------------------
    # Flexible JSON data storage
    # ---------------------------------------------------------------
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Arbitrary JSON payload with Square payment details or metadata."
    )

    # ---------------------------------------------------------------
    # Audit Timestamps
    # ---------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when the payment record was created."
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when the payment record was last updated."
    )

    # ---------------------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------------------
    def mark_completed(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark this payment as successfully completed."""
        self.status = self.STATUS_COMPLETED
        if details:
            self.extra_data.update(details)

    def mark_failed(self, reason: str) -> None:
        """Mark this payment as failed, storing a reason."""
        self.status = self.STATUS_FAILED
        self.extra_data["failure_reason"] = reason

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} "
            f"plan_type={self.plan_type} "
            f"status={self.status} "
            f"amount={self.amount}>"
        )
