# ================================================================
# File: checkout.py
# Path: app/models/checkout.py
# Description: SQLAlchemy model storing Square checkout bundle metadata.
# ================================================================

import uuid

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.models import Base


class SquareCheckoutLink(Base):
    __tablename__ = "square_checkout_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(String(64), nullable=True)
    url = Column(String(2048), nullable=True)
    plan_type = Column(String(64), nullable=False, default="subscription")
    cta_label = Column(String(128), nullable=True, default="Open Secure Checkout")
    features = Column(JSON, default=list, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
