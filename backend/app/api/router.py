from fastapi import APIRouter
from app.domains.documents.router import router as documents_router
from app.domains.conversations.router import router as conversations_router

router = APIRouter()
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])