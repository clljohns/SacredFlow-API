from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import Actor, get_current_actor, get_db_session
from ..models import Conversation, Message

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def fetch_last_message(db: Session, conversation_id: UUID) -> Optional[Message]:
    return (
        db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        .scalars()
        .first()
    )


@router.get("", response_model=schemas.ConversationList)
def list_conversations(
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db_session),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
):
    filters = []
    if actor.role == "affiliate":
        filters.append(Conversation.affiliate_id == actor.affiliate_id)

    if cursor:
        try:
            cursor_time = datetime.fromisoformat(cursor)
            filters.append(Conversation.created_at < cursor_time)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor format")

    stmt = select(Conversation).order_by(desc(Conversation.created_at)).limit(limit)
    if filters:
        stmt = stmt.where(and_(*filters))

    conversations = db.execute(stmt).scalars().all()
    items = []
    for conv in conversations:
        last_message = fetch_last_message(db, conv.id)
        items.append(
            schemas.ConversationOut(
                id=conv.id,
                customer=conv.customer,
                affiliate_id=conv.affiliate_id,
                created_at=conv.created_at,
                last_message=last_message,
            )
        )

    next_cursor = conversations[-1].created_at.isoformat() if len(conversations) == limit else None
    return schemas.ConversationList(items=items, next_cursor=next_cursor)
