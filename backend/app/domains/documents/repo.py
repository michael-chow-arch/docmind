from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from .model import Document, DocumentChunk, DocumentImage, DocumentTable

logger = get_logger(__name__)


class DocumentRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, doc: Document) -> None:
        self.db.add(doc)

    async def get(self, document_id: int) -> Document | None:
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_recent(self, limit: int = 50) -> list[Document]:
        stmt = select(Document).order_by(Document.id.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, doc: Document) -> None:
        await self.db.delete(doc)
        await self.db.flush()

    async def clear_assets(self, document_id: int) -> None:
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        await self.db.execute(delete(DocumentImage).where(DocumentImage.document_id == document_id))
        await self.db.execute(delete(DocumentTable).where(DocumentTable.document_id == document_id))

    async def add_chunk(self, chunk: DocumentChunk) -> None:
        self.db.add(chunk)

    async def list_chunks_without_embedding(self, document_id: int, limit: int = 200) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .where(DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
