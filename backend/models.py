import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db import Base


class SenderType(str, enum.Enum):
    customer = "customer"
    affiliate = "affiliate"
    admin = "admin"
    system = "system"


class MessageStatus(str, enum.Enum):
    received = "received"
    sent = "sent"
    delivered = "delivered"
    read = "read"


class Affiliate(Base):
    __tablename__ = "affiliates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    customers = relationship("Customer", back_populates="affiliate")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=True)

    affiliate = relationship("Affiliate", back_populates="customers")
    conversations = relationship("Conversation", back_populates="customer")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    customer = relationship("Customer", back_populates="conversations")
    affiliate = relationship("Affiliate")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type = Column(Enum(SenderType, name="sender_type"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(MessageStatus, name="message_status"), nullable=False, default=MessageStatus.received)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="messages")


Index("ix_messages_conversation_created", Message.conversation_id, Message.created_at.desc())
