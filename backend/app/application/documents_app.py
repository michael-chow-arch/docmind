from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from typing import Optional

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.config import settings
from app.db.uow import UnitOfWork
from app.domains.documents.model import Document, DocumentChunk
from app.domains.documents.repo import DocumentRepo
from app.infrastructure.storage.local_fs import LocalFileStorage
from app.infrastructure.document_processing.docling_processor import DoclingProcessor
from app.infrastructure.embeddings import get_embedding_provider
from app.domains.documents.vector_repo import VectorRepo

logger = get_logger(__name__)

class DocumentsApp:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.uow = UnitOfWork(db)
        self.repo = DocumentRepo(db)
        self.storage = LocalFileStorage()
        self.processor = DoclingProcessor()

    async def upload(self, filename: str, content: bytes) -> Document:
        logger.info(f"Uploading document: filename={filename}, size={len(content)} bytes")
        try:
            file_path = await self.storage.save_bytes("documents", filename, content)
            async with self.uow:
                doc = Document(
                    filename=filename,
                    file_path=file_path,
                    processing_status="pending",
                    error_message=None,
                    updated_at=datetime.utcnow(),
                )
                await self.repo.add(doc)
                await self.db.flush()
            logger.info(f"Document uploaded successfully: document_id={doc.id}, filename={filename}")
            return doc
        except Exception as e:
            logger.exception(f"Failed to upload document: filename={filename}, error={type(e).__name__}")
            raise

    async def list_recent(self, limit: int = 50) -> list[Document]:
        return await self.repo.list_recent(limit=limit)

    async def get(self, document_id: int) -> Document | None:
        return await self.repo.get(document_id)

    async def delete(self, document_id: int) -> bool:
        doc = await self.get(document_id)
        if not doc:
            return False

        async with self.uow:
            await self.repo.delete(doc)

        try:
            await self.storage.remove(doc.file_path)
            logger.debug(f"File deleted: {doc.file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete file (non-critical): file_path={doc.file_path}, error={type(e).__name__}")
        return True

    async def ingest(self, document_id: int) -> Document | None:
        logger.info(f"Starting ingestion: document_id={document_id}")
        doc = await self.get(document_id)
        if not doc:
            logger.warning(f"Document not found for ingestion: document_id={document_id}")
            return None

        async with self.uow:
            doc.processing_status = "processing"
            doc.error_message = None
            doc.updated_at = datetime.utcnow()

        try:
            if not await self.storage.exists(doc.file_path):
                raise FileNotFoundError(f"Missing file: {doc.file_path}")
            logger.debug(f"Processing document: document_id={document_id}, file_path={doc.file_path}")
            payload = await run_in_threadpool(self.processor.process, doc.file_path)
            logger.info(f"Document processed: document_id={document_id}, chunks={len(payload.get('chunks', []))}, pages={payload.get('pages')}")
        except Exception as e:
            logger.exception(f"Document processing failed: document_id={document_id}, error={type(e).__name__}")
            async with self.uow:
                doc.processing_status = "error"
                doc.error_message = str(e)
                doc.updated_at = datetime.utcnow()
            return doc

        chunks = payload["chunks"]

        async with self.uow:
            await self.repo.clear_assets(document_id)
            for c in chunks:
                await self.repo.add_chunk(
                    DocumentChunk(
                        document_id=document_id,
                        content=c.content,
                        page_number=c.page_number,
                        chunk_index=c.chunk_index,
                        meta=c.meta,
                        embedding=None,
                    )
                )
            doc.total_pages = payload.get("pages")
            doc.text_chunks_count = len(chunks)
            doc.images_count = 0
            doc.tables_count = 0
            doc.updated_at = datetime.utcnow()

        try:
            logger.info(f"Generating embeddings: document_id={document_id}, chunks={len(chunks)}")
            await self._embed_chunks(document_id)
            logger.info(f"Embeddings generated successfully: document_id={document_id}")
        except Exception as e:
            logger.exception(f"Embedding generation failed: document_id={document_id}, error={type(e).__name__}")
            async with self.uow:
                doc.processing_status = "error"
                doc.error_message = f"EmbeddingError: {str(e)}"
                doc.updated_at = datetime.utcnow()
            return doc

        async with self.uow:
            doc.processing_status = "completed"
            doc.error_message = None
            doc.updated_at = datetime.utcnow()

        logger.info(f"Ingestion completed: document_id={document_id}, chunks={doc.text_chunks_count}")
        return doc

    async def _embed_chunks(self, document_id: int, batch_size: int = 64) -> None:
        provider = get_embedding_provider()
        batch_count = 0

        while True:
            async with self.uow:
                rows = await self.repo.list_chunks_without_embedding(document_id, limit=batch_size)
                if not rows:
                    logger.debug(f"Embedding complete: document_id={document_id}, batches={batch_count}")
                    return
                texts = [r.content for r in rows]

            batch_count += 1
            logger.debug(f"Embedding batch {batch_count}: document_id={document_id}, chunks={len(texts)}")
            vecs = await run_in_threadpool(provider.embed_many, texts)

            async with self.uow:
                for r, v in zip(rows, vecs):
                    r.embedding = v
    
    async def search(
        self,
        query: str,
        document_id: Optional[int],
        top_k: int = 5,
    ) -> list[dict]:
        original_query = query
        if settings.QUERY_REWRITE_ENABLED:
            query = await run_in_threadpool(self._rewrite_query, query)
            if query != original_query:
                logger.info(
                    f"Query rewritten: original={original_query[:200]}, "
                    f"rewritten={query[:200]}"
                )
        
        logger.info(f"Vector search: query_length={len(query)}, document_id={document_id}, top_k={top_k}")
        try:
            provider = get_embedding_provider()
            query_vec = await run_in_threadpool(provider.embed_one, query)

            repo = VectorRepo(self.db)
            results = await repo.search_similar(
                query_embedding=query_vec,
                document_id=document_id,
                k=top_k * 10,
            )
            aggregated_results = self._aggregate_by_page(results)
            
            filtered_results = self._apply_diversity_filter(aggregated_results, top_k)
            
            logger.info(f"Vector search completed: results={len(filtered_results)}, document_id={document_id}")
            return filtered_results
        except Exception as e:
            logger.exception(f"Vector search failed: document_id={document_id}, error={type(e).__name__}")
            raise

    def _aggregate_by_page(self, results: list[dict]) -> list[dict]:
        if not results:
            return results

        groups: dict[tuple[int, int], list[dict]] = {}
        ungrouped: list[dict] = []

        for result in results:
            page_num = result.get("page_number")
            doc_id = result.get("document_id")
            
            if page_num is not None and doc_id is not None:
                key = (doc_id, page_num)
                if key not in groups:
                    groups[key] = []
                groups[key].append(result)
            else:
                ungrouped.append(result)

        aggregated = []

        for (doc_id, page_num), chunks in groups.items():
            chunks_sorted = sorted(chunks, key=lambda x: x.get("chunk_index", 0))
            
            merged_content = "\n".join(c.get("content", "") for c in chunks_sorted)
            max_score = max(c.get("score", 0.0) for c in chunks_sorted)
            first_chunk = chunks_sorted[0]
            aggregated.append({
                "chunk_id": first_chunk.get("chunk_id"),
                "document_id": doc_id,
                "content": merged_content,
                "page_number": page_num,
                "chunk_index": first_chunk.get("chunk_index"),
                "meta": first_chunk.get("meta", {}),
                "distance": min(c.get("distance", 1.0) for c in chunks_sorted),
                "score": max_score,
            })

        all_results = aggregated + ungrouped
        all_results.sort(key=lambda x: (-x.get("score", 0.0), x.get("chunk_index", 0)))

        return all_results

    def _apply_diversity_filter(self, results: list[dict], max_results: int) -> list[dict]:
        if not results:
            return results

        filtered = []
        page_counts: dict[int | None, int] = {}

        for result in results:
            page_num = result.get("page_number")
            count = page_counts.get(page_num, 0)

            if count < 2:
                filtered.append(result)
                page_counts[page_num] = count + 1
                if len(filtered) >= max_results:
                    break

        return filtered

    def _rewrite_query(self, query: str) -> str:
        if not query or not query.strip():
            return query

        try:
            if settings.OPENAI_API_KEY:
                return self._rewrite_with_openai(query)
            else:
                return self._rewrite_heuristic(query)
        except Exception as e:
            logger.warning(f"Query rewrite failed, using original: {type(e).__name__}")
            return query

    def _rewrite_with_openai(self, query: str) -> str:
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.OPENAI_API_KEY
            )
            
            prompt = """Rewrite the following search query into a concise, technical search query suitable for document retrieval.

Rules:
- Keep key nouns, proper nouns, and technical terms
- Remove filler words (the, a, an, is, are, what, how, etc.)
- Preserve quoted phrases exactly
- Do NOT answer the question, only rewrite it
- Keep the query under 200 characters
- Output only the rewritten query, no explanation

Query: {query}

Rewritten query:""".format(query=query)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3,
            )
            
            rewritten = response.choices[0].message.content.strip()
            if rewritten and len(rewritten) <= 200:
                return rewritten
            else:
                logger.warning(f"OpenAI rewrite too long or empty, using heuristic")
                return self._rewrite_heuristic(query)
                
        except Exception as e:
            logger.debug(f"OpenAI rewrite failed: {type(e).__name__}, falling back to heuristic")
            return self._rewrite_heuristic(query)

    def _rewrite_heuristic(self, query: str) -> str:
        import re
        filler_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "having", "do", "does", "did", "doing",
            "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
            "can", "could", "should", "would", "may", "might", "must",
            "this", "that", "these", "those",
            "and", "or", "but", "if", "then", "than",
            "to", "for", "of", "in", "on", "at", "by", "with", "from",
            "as", "so", "up", "out", "off", "over", "under", "above", "below",
        }
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        query_no_quotes = re.sub(r'"[^"]+"', " QUOTED_PLACEHOLDER ", query)
        words = re.findall(r'\b\w+\b', query_no_quotes.lower())
        meaningful_words = []
        for w in words:
            if w == "quoted_placeholder":
                meaningful_words.append("QUOTED_PLACEHOLDER")
            elif w not in filler_words and len(w) > 2:
                meaningful_words.append(w)
        result_parts = []
        quote_idx = 0
        for word in meaningful_words:
            if word == "QUOTED_PLACEHOLDER":
                if quote_idx < len(quoted_phrases):
                    result_parts.append(f'"{quoted_phrases[quote_idx]}"')
                    quote_idx += 1
            else:
                result_parts.append(word)
        while quote_idx < len(quoted_phrases):
            result_parts.append(f'"{quoted_phrases[quote_idx]}"')
            quote_idx += 1
        
        rewritten = " ".join(result_parts)
        if not rewritten or len(rewritten) < len(query) * 0.3:
            return query
        if len(rewritten) > 200:
            rewritten = rewritten[:197] + "..."
        
        return rewritten.strip()
