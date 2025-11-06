# ================================================================
# File: communication.py
# Path: app/schemas/communication.py
# Description: Pydantic schemas for SacredFlow communications API payloads.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Direction = Literal["inbound", "outbound"]


class CommunicationBase(BaseModel):
    channel: str = Field(description="Primary channel for the communication, e.g. chat or email.")
    direction: Direction = Field(description="Whether the conversation originated inbound or outbound.")
    body: str = Field(description="Message payload for the communication.")
    subject: Optional[str] = Field(default=None, description="Optional subject line (usually for email).")
    status: Optional[str] = Field(default="queued", description="Current delivery status (queued, delivered, etc).")
    user_id: Optional[str] = Field(default=None, description="Portal user identifier associated with this entry.")
    contact_email: Optional[EmailStr] = Field(default=None, description="Contact email for the conversation.")
    contact_name: Optional[str] = Field(default=None, description="Contact name for the conversation.")
    external_reference: Optional[str] = Field(
        default=None, description="Reference to an external system (Square, CRM, etc)."
    )
    meta: Dict[str, Any] = Field(default_factory=dict, description="Supplemental metadata captured alongside the entry.")
    attachments: List[Dict[str, Any]] = Field(
        default_factory=list, description="Optional attachments forwarded with the message."
    )


class CommunicationCreate(CommunicationBase):
    is_read: Optional[bool] = Field(default=None, description="Override read state; defaults based on direction.")


class CommunicationUpdate(BaseModel):
    status: Optional[str] = Field(default=None)
    is_read: Optional[bool] = Field(default=None)
    meta: Optional[Dict[str, Any]] = Field(default=None)


class CommunicationRead(CommunicationBase):
    id: str
    created_at: datetime
    updated_at: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)


class ChatMessageRequest(BaseModel):
    message: str = Field(description="Visitor supplied chat message.")
    visitor_email: Optional[EmailStr] = Field(default=None, description="Optional email for follow-up.")
    visitor_name: Optional[str] = Field(default=None, description="Optional visitor name (if collected).")
    page: Optional[str] = Field(default=None, description="Page URL where the chat was submitted.")
    forward_to_square: bool = Field(default=True, description="Forward chat payload to the Square inbox webhook.")
    forward_to_primary: bool = Field(default=True, description="Forward chat payload to the configured primary email.")
    forward_to_mobile: bool = Field(default=False, description="Forward chat payload to the mobile push webhook.")
    primary_email: Optional[EmailStr] = Field(default=None, description="Override for primary email routing target.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata describing the chat context.")


class ChatRelayResponse(BaseModel):
    communication: CommunicationRead
    forwarded: Dict[str, bool]
    warnings: List[str] = Field(default_factory=list)
