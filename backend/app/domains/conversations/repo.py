from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.domains.conversations.model import Conversation, ConversationMessage, AnswerSession, AnswerSessionVO

logger = get_logger(__name__)


class ConversationRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conversation(self, conversation_id: uuid.UUID, user_id: str) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_conversation(
        self,
        user_id: str,
        title: str,
        document_id: Optional[int] = None,
    ) -> Conversation:
        logger.debug(f"Creating conversation: user_id={user_id}, title={title[:50]}, document_id={document_id}")
        conv = Conversation(
            user_id=user_id,
            title=title,
            document_id=document_id,
        )
        self.db.add(conv)
        await self.db.flush()
        logger.info(f"Conversation created: id={conv.id}, user_id={user_id}")
        return conv

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        meta: Optional[dict] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            meta=meta or {},
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def list_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int = 20,
    ) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_conversation_updated_at(self, conversation_id: uuid.UUID) -> None:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conv = result.scalars().first()
        if conv:
            conv.updated_at = datetime.utcnow()
            await self.db.flush()


class AnswerSessionRepo:
    def __init__(self, db: AsyncSession, ttl_seconds: int | None = None):
        self.db = db
        self.ttl_seconds = ttl_seconds or settings.SESSION_TTL_SECONDS
        logger.debug(f"AnswerSessionRepo initialized: ttl_seconds={self.ttl_seconds}")
    
    async def create(
        self,
        document_id: Optional[int],
        topic_summary: str,
        active_chunk_ids: list[int],
    ) -> AnswerSessionVO:
        import uuid as uuid_lib
        session_id = str(uuid_lib.uuid4())
        now = datetime.utcnow()
        
        db_session = AnswerSession(
            session_id=session_id,
            document_id=document_id,
            topic_summary=topic_summary,
            active_chunk_ids=active_chunk_ids,
            created_at=now,
            updated_at=now,
        )
        self.db.add(db_session)
        await self.db.flush()
        return AnswerSessionVO.from_model(db_session)
    
    async def get(self, session_id: str) -> AnswerSessionVO | None:
        stmt = select(AnswerSession).where(AnswerSession.session_id == session_id)
        result = await self.db.execute(stmt)
        db_session = result.scalars().first()
        
        if not db_session:
            return None
        if self.is_expired(db_session):
            logger.info(f"Session expired, deleting: session_id={session_id}")
            await self.db.delete(db_session)
            await self.db.flush()
            return None
        
        logger.debug(f"Session retrieved: session_id={session_id}, document_id={db_session.document_id}")
        return AnswerSessionVO.from_model(db_session)
    
    async def update(
        self,
        session_id: str,
        topic_summary: str,
        active_chunk_ids: list[int],
    ) -> AnswerSessionVO | None:
        stmt = select(AnswerSession).where(AnswerSession.session_id == session_id)
        result = await self.db.execute(stmt)
        db_session = result.scalars().first()
        
        if not db_session:
            return None
        if self.is_expired(db_session):
            await self.db.delete(db_session)
            await self.db.flush()
            return None
        db_session.topic_summary = topic_summary
        db_session.active_chunk_ids = active_chunk_ids
        db_session.updated_at = datetime.utcnow()
        await self.db.flush()
        
        return AnswerSessionVO.from_model(db_session)
    
    async def delete(self, session_id: str) -> bool:
        stmt = select(AnswerSession).where(AnswerSession.session_id == session_id)
        result = await self.db.execute(stmt)
        db_session = result.scalars().first()
        
        if not db_session:
            return False
        
        await self.db.delete(db_session)
        await self.db.flush()
        return True
    
    def is_expired(self, session: AnswerSession) -> bool:
        age_seconds = (datetime.utcnow() - session.created_at).total_seconds()
        return age_seconds > self.ttl_seconds
