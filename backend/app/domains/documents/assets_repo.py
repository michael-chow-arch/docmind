from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.documents.model import DocumentImage, DocumentTable


class AssetsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_images(self, document_id: int) -> list[DocumentImage]:
        stmt = select(DocumentImage).where(DocumentImage.document_id == document_id).order_by(DocumentImage.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_tables(self, document_id: int) -> list[DocumentTable]:
        stmt = select(DocumentTable).where(DocumentTable.document_id == document_id).order_by(DocumentTable.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
