# ================================================================
# File: catalog.py
# Path: app/schemas/catalog.py
# Description: Pydantic schemas for Square catalog synchronization endpoints.
# Author: SacredFlow Engineering
# ================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class SquareCatalogItemOut(BaseModel):
    id: uuid.UUID
    square_id: str = Field(alias="squareId")
    variation_id: Optional[str] = Field(default=None, alias="variationId")
    name: str
    description: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, alias="priceCents")
    currency: Optional[str] = None
    is_deleted: bool = Field(alias="isDeleted")
    product_id: Optional[uuid.UUID] = Field(default=None, alias="productId")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class SquareCatalogSyncResponse(BaseModel):
    processed: int
    created: int
    updated: int
    deactivated: int
    environment: Optional[str] = None
    errors: List[str]


class SquareCatalogListResponse(BaseModel):
    items: List[SquareCatalogItemOut]
    count: int

