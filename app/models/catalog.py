# ================================================================
# File: catalog.py
# Path: app/models/catalog.py
# Description: SQLAlchemy models for Square catalog synchronization
#              and SacredFlow product mappings.
# Author: SacredFlow Engineering
# ================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Product(Base):
    """SacredFlow internal representation of products tied to Square items."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    square_catalog_object_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    square_catalog_variation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    square_item: Mapped["SquareCatalogItem"] = relationship(
        "SquareCatalogItem", back_populates="product", uselist=False
    )


class SquareCatalogItem(Base):
    """Snapshot of Square catalog items synchronized into SacredFlow."""

    __tablename__ = "square_catalog_items"
    __table_args__ = (
        UniqueConstraint("square_id", name="uq_square_catalog_items_square_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    square_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    variation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product: Mapped[Optional[Product]] = relationship("Product", back_populates="square_item")

    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

