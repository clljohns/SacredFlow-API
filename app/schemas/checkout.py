# ================================================================
# File: checkout.py
# Path: app/schemas/checkout.py
# Description: Pydantic schemas for Square checkout bundles.
# ================================================================

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheckoutLinkBase(BaseModel):
    slug: str = Field(..., max_length=64)
    title: str
    description: Optional[str] = None
    price: Optional[str] = None
    url: Optional[str] = None
    plan_type: str = "subscription"
    cta_label: Optional[str] = "Open Secure Checkout"
    features: List[str] = Field(default_factory=list)
    sort_order: int = 0


class CheckoutLinkRead(CheckoutLinkBase):
    id: UUID

    class Config:
        from_attributes = True


class CheckoutLinkUpsert(CheckoutLinkBase):
    pass
