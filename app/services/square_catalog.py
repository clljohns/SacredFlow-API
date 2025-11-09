# ================================================================
# File: square_catalog.py
# Path: app/services/square_catalog.py
# Description: Synchronizes Square catalog items into SacredFlow storage.
# Author: SacredFlow Engineering
# ================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.square import SquareConfigurationError, call_square, get_square_client
from app.models.catalog import Product, SquareCatalogItem

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CatalogSyncStats:
    processed: int
    created: int
    updated: int
    deactivated: int
    errors: List[str]
    environment: Optional[str] = None


class SquareCatalogSyncService:
    """Service responsible for pulling Square catalog data and persisting it."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync(self) -> CatalogSyncStats:
        try:
            client = get_square_client()
        except SquareConfigurationError as exc:
            logger.error("Square catalog sync aborted: %s", exc)
            return CatalogSyncStats(
                processed=0,
                created=0,
                updated=0,
                deactivated=0,
                errors=[str(exc)],
            )

        response = await call_square(
            "catalog.list_catalog", client.catalog.list_catalog, types="ITEM,ITEM_VARIATION"
        )

        if response.is_error():
            error_messages = [err.get("detail", str(err)) for err in response.errors or []]
            logger.error("Square catalog sync failed: %s", error_messages)
            return CatalogSyncStats(
                processed=0,
                created=0,
                updated=0,
                deactivated=0,
                errors=error_messages or ["Unknown Square error"],
            )

        objects = response.body.get("objects", []) if response.body else []

        existing_items = await self._load_existing_items()
        seen_ids: set[str] = set()

        created = 0
        updated = 0
        deactivated = 0

        for obj in objects:
            object_type = obj.get("type")
            if object_type != "ITEM":
                continue

            square_id = obj.get("id")
            if not square_id:
                continue

            seen_ids.add(square_id)
            item_data = obj.get("item_data", {})
            name = item_data.get("name", "Unnamed Item")
            description = item_data.get("description")
            variations = item_data.get("variations", []) or []

            variation_id = None
            price_cents = None
            currency = None

            if variations:
                variation = variations[0]
                variation_id = variation.get("id")
                money = (variation.get("item_variation_data") or {}).get("price_money") or {}
                price_cents = money.get("amount")
                currency = money.get("currency")

            record = existing_items.get(square_id)
            if record:
                is_updated = await self._update_record(
                    record,
                    variation_id=variation_id,
                    name=name,
                    description=description,
                    price_cents=price_cents,
                    currency=currency,
                    version=int(obj.get("version", record.version)),
                    payload=obj,
                    is_deleted=bool(obj.get("is_deleted", False)),
                )
                if is_updated:
                    updated += 1
            else:
                await self._create_record(
                    square_id=square_id,
                    variation_id=variation_id,
                    name=name,
                    description=description,
                    price_cents=price_cents,
                    currency=currency,
                    version=int(obj.get("version", 0)),
                    payload=obj,
                    is_deleted=bool(obj.get("is_deleted", False)),
                )
                created += 1

        # Mark stale items as deleted
        for square_id, record in existing_items.items():
            if square_id not in seen_ids and not record.is_deleted:
                record.is_deleted = True
                record.updated_at = datetime.now(tz=UTC)
                deactivated += 1

        await self.session.commit()

        return CatalogSyncStats(
            processed=len(seen_ids),
            created=created,
            updated=updated,
            deactivated=deactivated,
            errors=[],
            environment=client.configuration.environment if hasattr(client, "configuration") else None,
        )

    async def _load_existing_items(self) -> Dict[str, SquareCatalogItem]:
        result = await self.session.execute(select(SquareCatalogItem))
        records = result.scalars().all()
        return {record.square_id: record for record in records}

    async def _create_record(
        self,
        *,
        square_id: str,
        variation_id: Optional[str],
        name: str,
        description: Optional[str],
        price_cents: Optional[int],
        currency: Optional[str],
        version: int,
        payload: Dict[str, Any],
        is_deleted: bool,
    ) -> SquareCatalogItem:
        record = SquareCatalogItem(
            square_id=square_id,
            variation_id=variation_id,
            name=name,
            description=description,
            price_cents=price_cents,
            currency=currency,
            version=version,
            raw_payload=payload,
            is_deleted=is_deleted,
        )
        if not is_deleted:
            await self._ensure_product_binding(record)

        self.session.add(record)
        return record

    async def _update_record(
        self,
        record: SquareCatalogItem,
        *,
        variation_id: Optional[str],
        name: str,
        description: Optional[str],
        price_cents: Optional[int],
        currency: Optional[str],
        version: int,
        payload: Dict[str, Any],
        is_deleted: bool,
    ) -> bool:
        has_changes = False

        for attr, new_value in (
            ("variation_id", variation_id),
            ("name", name),
            ("description", description),
            ("price_cents", price_cents),
            ("currency", currency),
            ("version", version),
            ("is_deleted", is_deleted),
        ):
            if getattr(record, attr) != new_value:
                setattr(record, attr, new_value)
                has_changes = True

        if record.raw_payload != payload:
            record.raw_payload = payload
            has_changes = True

        if has_changes:
            record.updated_at = datetime.now(tz=UTC)
            if not is_deleted:
                await self._ensure_product_binding(record)

        return has_changes

    async def _ensure_product_binding(self, record: SquareCatalogItem) -> None:
        """Ensure an internal product exists for the Square item."""

        if record.product_id:
            return

        price_cents = record.price_cents or 0
        currency = record.currency or "USD"

        product = Product(
            name=record.name,
            description=record.description,
            price_cents=price_cents,
            currency=currency,
            square_catalog_object_id=record.square_id,
            square_catalog_variation_id=record.variation_id,
            attributes={"source": "square"},
        )
        self.session.add(product)
        await self.session.flush()
        record.product_id = product.id

