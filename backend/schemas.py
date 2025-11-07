import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from .models import MessageStatus, SenderType


class AffiliateOut(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr

    model_config = {"from_attributes": True}


class CustomerBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class CustomerOut(CustomerBase):
    id: uuid.UUID
    affiliate_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: SenderType
    content: str
    status: MessageStatus
    metadata: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    customer: CustomerOut
    affiliate_id: Optional[uuid.UUID]
    created_at: datetime
    last_message: Optional[MessageOut] = None

    model_config = {"from_attributes": True}


class RelayRequest(BaseModel):
    message: str = Field(..., min_length=1)
    visitorEmail: Optional[EmailStr] = Field(default=None, alias="visitorEmail")
    visitorName: Optional[str] = None
    page: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelayResponse(BaseModel):
    entry: MessageOut
    conversation: ConversationOut
    warnings: List[str] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    content: str = Field(..., min_length=1)
    sender_type: SenderType


class ConversationList(BaseModel):
    items: List[ConversationOut]
    next_cursor: Optional[str] = None


class MessagesList(BaseModel):
    items: List[MessageOut]
    next_cursor: Optional[str] = None
