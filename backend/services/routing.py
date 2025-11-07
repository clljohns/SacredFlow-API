from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Conversation, Customer


def get_or_create_customer(db: Session, email: str, name: Optional[str] = None) -> Customer:
    customer = db.execute(select(Customer).where(Customer.email == email)).scalar_one_or_none()
    if customer:
        if name and not customer.name:
            customer.name = name
            db.add(customer)
            db.commit()
            db.refresh(customer)
        return customer

    customer = Customer(email=email, name=name)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_or_create_conversation(db: Session, customer: Customer) -> Conversation:
    conversation = (
        db.execute(
            select(Conversation)
            .where(Conversation.customer_id == customer.id)
            .order_by(Conversation.created_at.desc())
        ).scalars().first()
    )
    if conversation:
        if not conversation.affiliate_id and customer.affiliate_id:
            conversation.affiliate_id = customer.affiliate_id
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        return conversation

    conversation = Conversation(customer_id=customer.id, affiliate_id=customer.affiliate_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation
