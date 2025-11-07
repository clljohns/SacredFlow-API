import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db


class Actor(BaseModel):
    role: str
    affiliate_id: Optional[uuid.UUID] = None


def get_current_actor(
    x_role: Optional[str] = Header(default=None, alias="x-role"),
    x_affiliate_id: Optional[str] = Header(default=None, alias="x-affiliate-id"),
) -> Actor:
    if not x_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="x-role header required")
    role = x_role.lower()
    if role not in {"super_admin", "affiliate"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role header")

    affiliate_id = None
    if role == "affiliate":
        if not x_affiliate_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="x-affiliate-id header required")
        try:
            affiliate_id = uuid.UUID(x_affiliate_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid affiliate id header")

    return Actor(role=role, affiliate_id=affiliate_id)


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db
