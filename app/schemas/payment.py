# ================================================================
# File: payment.py
# Path: app/schemas/payment.py
# Description: Pydantic schemas for Square payment flow.
# ================================================================

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class PaymentBase(BaseModel):
    customer_email: Optional[EmailStr] = None
    plan_type: str = "subscription"
    amount: int = Field(..., description="Amount in cents")
    status: str = "pending"


class PaymentRead(PaymentBase):
    id: UUID
    square_payment_id: Optional[str] = None
    metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreateRequest(BaseModel):
    token: str
    planType: str = "subscription"
    amount: float = 88.0
    customerEmail: Optional[EmailStr] = None
    metadata: dict = Field(default_factory=dict)


class PaymentConfirmRequest(BaseModel):
    squarePaymentId: str
    status: str = "COMPLETED"
    metadata: dict = Field(default_factory=dict)
