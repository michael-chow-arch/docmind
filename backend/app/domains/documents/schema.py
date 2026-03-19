from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    file_path: str
    upload_date: datetime
    updated_at: datetime
    processing_status: str
    error_message: str | None
    total_pages: int | None
    text_chunks_count: int
    images_count: int
    tables_count: int


class DocumentListOut(BaseModel):
    items: list[DocumentOut]


class IngestResponse(BaseModel):
    status: str
    document_id: int
    processing_status: str

class DocumentSearchRequest(BaseModel):
    query: str
    document_id: Optional[int] = None
    top_k: int = 5


class DocumentSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    content: str
    page_number: Optional[int]
    chunk_index: int
    score: float


class DocumentAnswerRequest(BaseModel):
    question: str
    document_id: Optional[int] = None
    top_k: int = 5
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None


class Citation(BaseModel):
    chunk_id: int
    page_number: Optional[int]


class AnswerContent(BaseModel):
    summary: str
    key_points: list[str]


class SessionInfo(BaseModel):
    session_id: str
    is_follow_up: bool


class ConversationInfo(BaseModel):
    id: str
    title: str
    updated_at: datetime


class DocumentAnswerResponse(BaseModel):
    answer: AnswerContent
    citations: list[Citation]
    session: SessionInfo
    conversation: Optional[ConversationInfo] = None