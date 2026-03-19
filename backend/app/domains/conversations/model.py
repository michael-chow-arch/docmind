from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Integer, Text, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_conversations_user_updated", "user_id", "updated_at"),)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_conversation_messages_conv_created", "conversation_id", "created_at"),)


class AnswerSession(Base):
    __tablename__ = "answer_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    topic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    active_chunk_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_answer_sessions_created_at", "created_at"),)


from dataclasses import dataclass
from typing import Optional


@dataclass
class AnswerSessionVO:
    session_id: str
    document_id: Optional[int]
    topic_summary: str
    active_chunk_ids: list[int]
    created_at: datetime
    last_updated_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "document_id": self.document_id,
            "topic_summary": self.topic_summary,
            "active_chunk_ids": self.active_chunk_ids,
            "created_at": self.created_at.isoformat(),
            "last_updated_at": self.last_updated_at.isoformat(),
        }
    
    @classmethod
    def from_model(cls, model: AnswerSession) -> "AnswerSessionVO":
        return cls(
            session_id=model.session_id,
            document_id=model.document_id,
            topic_summary=model.topic_summary,
            active_chunk_ids=model.active_chunk_ids,
            created_at=model.created_at,
            last_updated_at=model.updated_at,
        )
