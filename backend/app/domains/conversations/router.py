from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header

from app.api.deps import get_conversations_app
from app.application.conversations_app import ConversationsApp
from app.core.exceptions import NotFoundError
from app.domains.conversations.schema import (
    ConversationOut,
    MessageOut,
    CreateConversationRequest,
    ConversationListResponse,
    ConversationDetailResponse,
    AppendMessageRequest,
)

router = APIRouter()


def get_user_id(x_user_id: str | None = Header(None, alias="X-User-Id")) -> str:
    return x_user_id or "default"


@router.post("", response_model=ConversationOut)
async def create_conversation(
    req: CreateConversationRequest,
    app: ConversationsApp = Depends(get_conversations_app),
    user_id: str = Depends(get_user_id),
):
    conv = await app.create_conversation(
        user_id=user_id,
        title=req.title,
        document_id=req.document_id,
    )
    return ConversationOut.model_validate(conv)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    app: ConversationsApp = Depends(get_conversations_app),
    user_id: str = Depends(get_user_id),
):
    conversations = await app.list_conversations(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    
    return ConversationListResponse(
        items=[ConversationOut.model_validate(c) for c in conversations],
        limit=limit,
        offset=offset,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    app: ConversationsApp = Depends(get_conversations_app),
    user_id: str = Depends(get_user_id),
):
    try:
        conv, messages = await app.get_conversation(conversation_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return ConversationDetailResponse(
        conversation=ConversationOut.model_validate(conv),
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def append_message(
    conversation_id: str,
    req: AppendMessageRequest,
    app: ConversationsApp = Depends(get_conversations_app),
    user_id: str = Depends(get_user_id),
):
    try:
        msg = await app.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=req.role,
            content=req.content,
            meta=req.meta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return MessageOut.model_validate(msg)
