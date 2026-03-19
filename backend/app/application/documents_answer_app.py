from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.uow import UnitOfWork
from app.application.documents_app import DocumentsApp
from app.application.conversations_app import ConversationsApp
from app.application.answer_chunk_aggregator import AnswerChunkAggregator, RetrievedChunk
from app.application.follow_up_detector import FollowUpDetector
from app.domains.conversations.repo import AnswerSessionRepo
from app.domains.documents.model import DocumentChunk

logger = get_logger(__name__)


class DocumentsAnswerApp:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.uow = UnitOfWork(db)
        self.documents_app = DocumentsApp(db)
        self.conversations_app = ConversationsApp(db)
        self.answer_session_repo = AnswerSessionRepo(db)
        self.follow_up_detector = FollowUpDetector()

    async def answer(
        self,
        question: str,
        document_id: Optional[int],
        top_k: int = 5,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id: str = "default",
    ) -> dict:
        logger.info(
            f"Answer generation: question_length={len(question)}, document_id={document_id}, "
            f"top_k={top_k}, session_id={session_id}, conversation_id={conversation_id}, user_id={user_id}"
        )
        conv_uuid = await self._resolve_conversation(conversation_id, document_id, user_id)
        try:
            session_vo, is_follow_up, search_results, topic_summary = await self._retrieve_chunks(
                question, document_id, top_k, session_id
            )
            if not search_results:
                return self._no_chunks_response(session_id or "", is_follow_up)

            context, citations = self._build_context_and_citations(question, search_results)
            answer = await run_in_threadpool(
                self._generate_answer,
                question=question,
                context=context,
                citations=citations,
                is_follow_up=is_follow_up,
                topic_summary=topic_summary,
            )
            final_session_id = await self._persist_session(
                session_vo, is_follow_up, document_id, citations, answer
            )
            answer["session"] = {"session_id": final_session_id, "is_follow_up": is_follow_up}

            if conversation_id and conv_uuid:
                conv = await self._append_to_conversation(
                    conversation_id, user_id, question, answer, citations
                )
                answer["conversation"] = self._conv_to_info(conv)
            elif not conversation_id:
                conv = await self._create_and_append_conversation(
                    user_id, document_id, question, answer, citations
                )
                answer["conversation"] = self._conv_to_info(conv)

            logger.info(f"Answer generated: document_id={document_id}, citations={len(citations)}, session_id={final_session_id}")
            return answer
        except Exception as e:
            logger.exception(f"Answer generation failed: document_id={document_id}, error={type(e).__name__}")
            return self._error_response(session_id or "")

    async def _resolve_conversation(
        self, conversation_id: Optional[str], document_id: Optional[int], user_id: str
    ) -> uuid.UUID | None:
        if not conversation_id:
            return None
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            logger.warning(f"Invalid conversation ID: {conversation_id}")
            raise
        try:
            conv, _ = await self.conversations_app.get_conversation(conversation_id, user_id)
        except NotFoundError:
            raise ValueError("Conversation not found")
        if conv.document_id is not None and conv.document_id != document_id:
            raise ValueError("Document ID mismatch")
        return conv_uuid

    async def _retrieve_chunks(
        self,
        question: str,
        document_id: Optional[int],
        top_k: int,
        session_id: Optional[str],
    ) -> tuple:
        session_vo = await self.answer_session_repo.get(session_id) if session_id else None
        is_follow_up = self.follow_up_detector.is_follow_up(question, session_vo, document_id)
        if is_follow_up and session_vo:
            search_results = await self._retrieve_follow_up_chunks(
                question=question,
                active_chunk_ids=session_vo.active_chunk_ids,
                document_id=document_id,
                top_k=top_k,
            )
            topic_summary = session_vo.topic_summary
        else:
            search_results = await self.documents_app.search(
                query=question, document_id=document_id, top_k=top_k
            )
            topic_summary = None
        return session_vo, is_follow_up, search_results, topic_summary

    def _build_context_and_citations(self, question: str, search_results: list[dict]) -> tuple[str, list[dict]]:
        retrieved: list[RetrievedChunk] = [
            {
                "chunk_id": r.get("chunk_id"),
                "content": r.get("content", ""),
                "page_number": r.get("page_number"),
                "score": r.get("score", 0.0),
            }
            for r in search_results
        ]
        scored = AnswerChunkAggregator(max_chunks=settings.ANSWER_MAX_CHUNKS).aggregate(
            question, retrieved
        )
        context_parts = []
        citations = []
        for chunk in scored:
            context_parts.append(f"[Chunk {chunk['chunk_id']}] {chunk['content']}")
            citations.append({"chunk_id": chunk["chunk_id"], "page_number": chunk["page_number"]})
        return "\n\n".join(context_parts), citations

    async def _persist_session(
        self,
        session_vo,
        is_follow_up: bool,
        document_id: Optional[int],
        citations: list[dict],
        answer: dict,
    ) -> str:
        active_chunk_ids = [c["chunk_id"] for c in citations]
        async with self.uow:
            if is_follow_up and session_vo:
                updated = await self.answer_session_repo.update(
                    session_id=session_vo.session_id,
                    topic_summary=answer["answer"]["summary"][:200],
                    active_chunk_ids=active_chunk_ids,
                )
                return updated.session_id if updated else session_vo.session_id
            else:
                new_session = await self.answer_session_repo.create(
                    document_id=document_id,
                    topic_summary=answer["answer"]["summary"][:200],
                    active_chunk_ids=active_chunk_ids,
                )
                return new_session.session_id

    async def _append_to_conversation(
        self,
        conversation_id: str,
        user_id: str,
        question: str,
        answer: dict,
        citations: list[dict],
    ):
        await self.conversations_app.append_message(
            conversation_id=conversation_id, user_id=user_id, role="user", content=question
        )
        await self.conversations_app.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=answer["answer"]["summary"],
            meta={"key_points": answer["answer"]["key_points"], "citations": citations},
        )
        conv, _ = await self.conversations_app.get_conversation(conversation_id, user_id)
        return conv

    async def _create_and_append_conversation(
        self,
        user_id: str,
        document_id: Optional[int],
        question: str,
        answer: dict,
        citations: list[dict],
    ):
        title = question[:40] + ("..." if len(question) > 40 else "")
        conv = await self.conversations_app.create_conversation(
            user_id=user_id, document_id=document_id, title=title
        )
        await self.conversations_app.append_message(
            conversation_id=str(conv.id), user_id=user_id, role="user", content=question
        )
        await self.conversations_app.append_message(
            conversation_id=str(conv.id),
            user_id=user_id,
            role="assistant",
            content=answer["answer"]["summary"],
            meta={"key_points": answer["answer"]["key_points"], "citations": citations},
        )
        conv, _ = await self.conversations_app.get_conversation(str(conv.id), user_id)
        return conv

    def _conv_to_info(self, conv) -> dict:
        return {
            "id": str(conv.id),
            "title": conv.title,
            "updated_at": conv.updated_at.isoformat(),
        }

    def _no_chunks_response(self, session_id: str, is_follow_up: bool) -> dict:
        return {
            "answer": {
                "summary": "I don't have enough information to answer this question based on the available documents.",
                "key_points": [],
            },
            "citations": [],
            "session": {"session_id": session_id, "is_follow_up": is_follow_up},
            "conversation": None,
        }

    def _error_response(self, session_id: str) -> dict:
        return {
            "answer": {
                "summary": "I encountered an error while generating an answer. Please try again or rephrase your question.",
                "key_points": [],
            },
            "citations": [],
            "session": {"session_id": session_id, "is_follow_up": False},
        }

    async def _retrieve_follow_up_chunks(
        self,
        question: str,
        active_chunk_ids: list[int],
        document_id: Optional[int],
        top_k: int,
    ) -> list[dict]:
        if not active_chunk_ids:
            return []
        stmt = select(DocumentChunk).where(DocumentChunk.id.in_(active_chunk_ids))
        if document_id is not None:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()
        results = []
        for chunk in chunks:
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "meta": chunk.meta or {},
                "score": 0.9,
            })
        
        return results[:top_k]

    def _generate_answer(
        self,
        question: str,
        context: str,
        citations: list[dict],
        is_follow_up: bool = False,
        topic_summary: Optional[str] = None,
    ) -> dict:
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set, cannot generate answer")
            return {
                "answer": {
                    "summary": "Answer generation requires OpenAI API key to be configured.",
                    "key_points": [],
                },
                "citations": citations,
            }
        
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.OPENAI_API_KEY
            )
            
            if is_follow_up and topic_summary:
                prompt = self._build_follow_up_prompt(question, context, topic_summary)
            else:
                prompt = self._build_initial_prompt(question, context)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            
            answer_text = response.choices[0].message.content.strip()
            try:
                answer_data = json.loads(answer_text)
                return {
                    "answer": {
                        "summary": answer_data.get("summary", ""),
                        "key_points": answer_data.get("key_points", []),
                    },
                    "citations": citations,
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM JSON response: {e}")
                return {
                    "answer": {
                        "summary": answer_text[:500] if answer_text else "Unable to generate answer.",
                        "key_points": [],
                    },
                    "citations": citations,
                }
                
        except Exception as e:
            logger.exception(f"LLM answer generation failed: {type(e).__name__}")
            return {
                "answer": {
                    "summary": "I encountered an error while generating an answer.",
                    "key_points": [],
                },
                "citations": citations,
            }

    def _build_initial_prompt(self, question: str, context: str) -> str:
        return f"""You are a document Q&A assistant. Answer the question based ONLY on the provided document chunks.

Rules:
1. Answer ONLY using information from the provided chunks. Do not use external knowledge.
2. If the chunks don't contain enough information, say so clearly.
3. Cite specific chunks using [Chunk X] format where X is the chunk_id.
4. Produce a structured JSON response with:
   - "summary": A concise answer (2-3 sentences)
   - "key_points": Array of 3-5 key points from the chunks

Question: {question}

Document Chunks:
{context}

Respond with valid JSON only, no markdown formatting:
{{
  "summary": "...",
  "key_points": ["...", "..."]
}}"""

    def _build_follow_up_prompt(self, question: str, context: str, topic_summary: str) -> str:
        return f"""You are answering a follow-up question within an ongoing discussion about a document.
The topic has already been established. Do NOT re-summarize the document or restate the full context.

Established Topic: {topic_summary}

Rules:
1. Answer ONLY using information from the provided chunks. Do not use external knowledge.
2. This is a follow-up question - focus on clarification, extension, or deepening the discussion.
3. Do NOT re-summarize the document or restate what was already discussed.
4. If the chunks don't contain enough information, say so clearly.
5. Cite specific chunks using [Chunk X] format where X is the chunk_id.
6. Produce a structured JSON response with:
   - "summary": A concise answer (2-3 sentences) that builds on the established topic
   - "key_points": Array of 3-5 key points that extend or clarify the discussion

Follow-up Question: {question}

Relevant Document Chunks:
{context}

Respond with valid JSON only, no markdown formatting:
{{
  "summary": "...",
  "key_points": ["...", "..."]
}}"""
