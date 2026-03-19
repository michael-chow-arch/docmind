from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Header

from app.api.deps import get_documents_app, get_documents_answer_app
from app.application.documents_app import DocumentsApp
from app.application.documents_answer_app import DocumentsAnswerApp
from .schema import (
    DocumentOut,
    DocumentListOut,
    DocumentSearchRequest,
    DocumentSearchResult,
    DocumentAnswerRequest,
    DocumentAnswerResponse,
    IngestResponse,
)

router = APIRouter()


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    app: DocumentsApp = Depends(get_documents_app),
):
    content = await file.read()
    doc = await app.upload(file.filename, content)
    return DocumentOut.model_validate(doc)


@router.get("", response_model=DocumentListOut)
async def list_documents(
    limit: int = 50,
    app: DocumentsApp = Depends(get_documents_app),
):
    docs = await app.list_recent(limit=limit)
    return DocumentListOut(items=[DocumentOut.model_validate(d) for d in docs])


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: int,
    app: DocumentsApp = Depends(get_documents_app),
):
    doc = await app.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.model_validate(doc)


@router.post("/{document_id}/ingest", response_model=IngestResponse)
async def ingest_document(
    document_id: int,
    app: DocumentsApp = Depends(get_documents_app),
):
    doc = await app.ingest(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return IngestResponse(status="ok", document_id=doc.id, processing_status=doc.processing_status)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    app: DocumentsApp = Depends(get_documents_app),
):
    ok = await app.delete(document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "ok"}


@router.post(
    "/search",
    response_model=list[DocumentSearchResult],
    summary="Semantic search over document chunks",
)
async def search_documents(
    req: DocumentSearchRequest,
    app: DocumentsApp = Depends(get_documents_app),
):
    results = await app.search(
        query=req.query,
        document_id=req.document_id,
        top_k=req.top_k,
    )
    return results


@router.post(
    "/answer",
    response_model=DocumentAnswerResponse,
    summary="Generate LLM-powered answer from document search",
)
async def answer_question(
    req: DocumentAnswerRequest,
    app: DocumentsAnswerApp = Depends(get_documents_answer_app),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    user_id = x_user_id or "default"
    
    try:
        result = await app.answer(
            question=req.question,
            document_id=req.document_id,
            top_k=req.top_k,
            session_id=req.session_id,
            conversation_id=req.conversation_id,
            user_id=user_id,
        )
        return DocumentAnswerResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
