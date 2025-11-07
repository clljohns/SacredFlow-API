# ================================================================
# File: checkout.py
# Path: app/routes/checkout.py
# Description: API endpoints for Square checkout bundle management.
# ================================================================

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.checkout import SquareCheckoutLink
from app.schemas import CheckoutLinkRead, CheckoutLinkUpsert
from app.services.checkout_seed import seed_checkout_links

router = APIRouter(prefix="/api/square/checkouts", tags=["Square Checkout"])


@router.get("/", response_model=List[CheckoutLinkRead])
async def list_checkout_links(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(SquareCheckoutLink).order_by(SquareCheckoutLink.sort_order, SquareCheckoutLink.created_at)
    )
    return rows.scalars().all()


@router.post("/", response_model=CheckoutLinkRead, status_code=status.HTTP_201_CREATED)
async def upsert_checkout_link(payload: CheckoutLinkUpsert, session: AsyncSession = Depends(get_session)):
    existing_stmt = await session.execute(
        select(SquareCheckoutLink).where(SquareCheckoutLink.slug == payload.slug)
    )
    record = existing_stmt.scalar_one_or_none()
    if record:
        for field, value in payload.model_dump().items():
            setattr(record, field, value)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    record = SquareCheckoutLink(**payload.model_dump())
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/seed", response_model=List[CheckoutLinkRead])
async def seed_checkout_data(session: AsyncSession = Depends(get_session)):
    await seed_checkout_links(session)
    rows = await session.execute(select(SquareCheckoutLink).order_by(SquareCheckoutLink.sort_order))
    return rows.scalars().all()
