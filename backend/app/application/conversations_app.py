from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.uow import UnitOfWork
from app.domains.conversations.model import Conversation, ConversationMessage
from app.domains.conversations.repo import ConversationRepo

logger = get_logger(__name__)


class ConversationsApp:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.uow = UnitOfWork(db)
        self.repo = ConversationRepo(db)
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        document_id: Optional[int] = None,
    ) -> Conversation:
        final_title = title or "New Conversation"
        
        async with self.uow:
            conv = await self.repo.create_conversation(
                user_id=user_id,
                title=final_title,
                document_id=document_id,
            )
        
        logger.info(f"Conversation created: id={conv.id}, user_id={user_id}")
        return conv
    
    async def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 20
        if offset < 0:
            offset = 0
        return await self.repo.list_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> tuple[Conversation, list[ConversationMessage]]:
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            raise ValueError("Invalid conversation ID format")
        conv = await self.repo.get_conversation(conv_uuid, user_id)
        if not conv:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Conversation not found")
        messages = await self.repo.list_messages(conv_uuid, limit=20)
        return conv, messages
    
    async def append_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        meta: Optional[dict] = None,
    ) -> ConversationMessage:
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            raise ValueError("Invalid conversation ID format")
        
        async with self.uow:
            conv = await self.repo.get_conversation(conv_uuid, user_id)
            if not conv:
                from app.core.exceptions import NotFoundError
                raise NotFoundError("Conversation not found")
            msg = await self.repo.add_message(
                conversation_id=conv_uuid,
                role=role,
                content=content,
                meta=meta,
            )
            await self.repo.update_conversation_updated_at(conv_uuid)
        
        logger.info(f"Message appended to conversation: conversation_id={conversation_id}, role={role}")
        return msg
