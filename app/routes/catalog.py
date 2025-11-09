# ================================================================
# File: catalog.py
# Path: app/routes/catalog.py
# Description: Endpoints for managing Square catalog synchronization.
# Author: SacredFlow Engineering
# ================================================================

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.catalog import SquareCatalogItem
from app.schemas.catalog import (
    SquareCatalogItemOut,
    SquareCatalogListResponse,
    SquareCatalogSyncResponse,
)
from app.services.square_catalog import CatalogSyncStats, SquareCatalogSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/square/catalog", tags=["square", "catalog"])


@router.post("/sync", response_model=SquareCatalogSyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_catalog_sync(session: AsyncSession = Depends(get_session)) -> SquareCatalogSyncResponse:
    """Fetch the latest catalog data from Square and store it locally."""

    service = SquareCatalogSyncService(session)
    stats: CatalogSyncStats = await service.sync()

    if stats.errors:
        logger.warning("Catalog sync completed with errors: %s", stats.errors)

    return SquareCatalogSyncResponse(**stats.__dict__)


@router.get("/items", response_model=SquareCatalogListResponse)
async def list_catalog_items(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_deleted: bool = Query(default=False, alias="includeDeleted"),
    session: AsyncSession = Depends(get_session),
) -> SquareCatalogListResponse:
    stmt = select(SquareCatalogItem).order_by(SquareCatalogItem.updated_at.desc())
    if not include_deleted:
        stmt = stmt.where(SquareCatalogItem.is_deleted.is_(False))
    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    items = result.scalars().all()

    return SquareCatalogListResponse(
        items=[SquareCatalogItemOut.model_validate(item) for item in items],
        count=len(items),
    )

