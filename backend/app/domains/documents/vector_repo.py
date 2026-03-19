from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.documents.model import DocumentChunk


class VectorRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_chunks(self, chunks: Sequence[DocumentChunk]) -> int:
        self.session.add_all(list(chunks))
        await self.session.flush()
        return len(chunks)

    @staticmethod
    def _to_pgvector_literal(values: list[float]) -> str:
        return "[" + ",".join(str(float(v)) for v in values) + "]"


    async def search_similar(
        self,
        query_embedding: list[float],
        document_id: Optional[int] = None,
        k: int = 5,
    ) -> list[dict]:
        q = self._to_pgvector_literal(query_embedding)

        if document_id is None:
            sql = text("""
            SELECT
                id,
                document_id,
                content,
                page_number,
                chunk_index,
                meta,
                (embedding <=> CAST(:q AS vector)) AS distance
            FROM document_chunks
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :k
            """)
            params = {"q": q, "k": k}
        else:
            sql = text("""
            SELECT
                id,
                document_id,
                content,
                page_number,
                chunk_index,
                meta,
                (embedding <=> CAST(:q AS vector)) AS distance
            FROM document_chunks
            WHERE document_id = :doc_id
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :k
            """)
            params = {"q": q, "doc_id": document_id, "k": k}

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()

        return [
            {
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "content": r["content"],
                "page_number": r["page_number"],
                "chunk_index": r["chunk_index"],
                "meta": r["meta"],
                "distance": float(r["distance"]) if r["distance"] is not None else None,
                "score": 1.0 - float(r["distance"]) if r["distance"] is not None else 0.0,
            }
            for r in rows
        ]