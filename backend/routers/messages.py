import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import Actor, get_current_actor, get_db_session
from ..models import Conversation, Message, MessageStatus, SenderType
from ..services import ai_assist, routing

router = APIRouter(tags=["messages"])


@router.post("/api/chat/relay", response_model=schemas.RelayResponse)
def relay_chat_message(payload: schemas.RelayRequest, db: Session = Depends(get_db_session)):
    if not payload.visitorEmail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="visitorEmail is required")

    customer = routing.get_or_create_customer(db, payload.visitorEmail, payload.visitorName)
    conversation = routing.get_or_create_conversation(db, customer)

    metadata_blob = None
    metadata_payload = payload.metadata or {}
    if payload.page:
        metadata_payload = {**metadata_payload, "page": payload.page}
    if metadata_payload:
        metadata_blob = json.dumps(metadata_payload)

    message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.customer,
        content=payload.message,
        status=MessageStatus.received,
        metadata=metadata_blob,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return schemas.RelayResponse(entry=message, conversation=conversation, warnings=[])


@router.get(
    "/api/conversations/{conversation_id}/messages",
    response_model=schemas.MessagesList,
)
def list_messages(
    conversation_id: str = Path(...),
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db_session),
):
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation id")

    conversation = db.get(Conversation, conv_uuid)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if actor.role == "affiliate" and conversation.affiliate_id != actor.affiliate_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view conversation")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return schemas.MessagesList(items=messages, next_cursor=None)


@router.post(
    "/api/conversations/{conversation_id}/reply",
    response_model=schemas.MessageOut,
)
async def reply_to_conversation(
    background_tasks: BackgroundTasks,
    request: schemas.ReplyRequest,
    conversation_id: str = Path(...),
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db_session),
):
    if actor.role == "affiliate" and request.sender_type != SenderType.affiliate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Affiliate replies must be sender_type=affiliate")

    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation id")

    conversation = db.get(Conversation, conv_uuid)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if actor.role == "affiliate" and conversation.affiliate_id != actor.affiliate_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reply to this conversation")

    message = Message(
        conversation_id=conversation.id,
        sender_type=request.sender_type,
        content=request.content,
        status=MessageStatus.sent,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    background_tasks.add_task(ai_assist.maybe_summarize, conversation.id)
    return message
