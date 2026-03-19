from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: str
    title: str
    document_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    meta: Optional[dict]
    created_at: datetime


class CreateConversationRequest(BaseModel):
    document_id: Optional[int] = None
    title: Optional[str] = None


class ConversationListResponse(BaseModel):
    items: list[ConversationOut]
    limit: int
    offset: int


class ConversationDetailResponse(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]


class AppendMessageRequest(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    meta: Optional[dict] = None
