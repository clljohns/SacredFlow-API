from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_db_session
from ..models import Customer

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=List[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db_session)):
    customers = db.execute(select(Customer).order_by(Customer.email)).scalars().all()
    return customers
