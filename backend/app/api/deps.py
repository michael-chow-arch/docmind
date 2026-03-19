from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.session import get_db
from app.application.documents_app import DocumentsApp
from app.application.documents_answer_app import DocumentsAnswerApp
from app.application.conversations_app import ConversationsApp


async def get_documents_app(
    db: AsyncSession = Depends(get_db)
) -> DocumentsApp:
    return DocumentsApp(db)


async def get_documents_answer_app(
    db: AsyncSession = Depends(get_db)
) -> DocumentsAnswerApp:
    return DocumentsAnswerApp(db)


async def get_conversations_app(
    db: AsyncSession = Depends(get_db)
) -> ConversationsApp:
    return ConversationsApp(db)
