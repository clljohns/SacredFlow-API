# ================================================================
# File: checkout_seed.py
# Path: app/services/checkout_seed.py
# Description: Helpers to seed Square checkout data from environment.
# ================================================================

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.checkout import SquareCheckoutLink


def _bundle_defaults():
    """Default Square checkout bundles to seed."""
    return [
        {
            "slug": "subscription",
            "title": "Sacred Synergy Subscription",
            "description": "Set-and-forget renewals with exclusive rituals and perks.",
            "price": "$88",
            "url": settings.SQUARE_SUBSCRIPTION_CHECKOUT_URL,
            "plan_type": "subscription",
            "features": [
                "Exclusive rituals & rewards",
                "Cancel anytime",
                "Hosted securely by Square",
            ],
            "sort_order": 0,
        },
        {
            "slug": "family",
            "title": "Double Sacred Synergy Bundle",
            "description": "Gift-ready double bundle with automatic shipping upgrades.",
            "price": "$168",
            "url": settings.SQUARE_FAMILY_CHECKOUT_URL,
            "plan_type": "bundle",
            "features": [
                "Multiple recipients supported",
                "Priority fallbacks with Square",
            ],
            "sort_order": 1,
        },
    ]


async def seed_checkout_links(session: AsyncSession) -> List[SquareCheckoutLink]:
    """Ensure checkout links exist based on environment configuration."""
    bundles = _bundle_defaults()
    created = []

    for bundle in bundles:
        if not bundle["url"]:
            continue

        existing = await session.execute(
            select(SquareCheckoutLink).where(SquareCheckoutLink.slug == bundle["slug"])
        )
        record = existing.scalar_one_or_none()

        if record:
            # Update in case environment variables have changed
            record.url = bundle["url"]
            record.price = bundle["price"]
            record.description = bundle["description"]
            record.features = bundle["features"]
            session.add(record)
            created.append(record)
            continue

        record = SquareCheckoutLink(**bundle)
        session.add(record)
        created.append(record)

    if created:
        await session.commit()
        for item in created:
            await session.refresh(item)

    return created
