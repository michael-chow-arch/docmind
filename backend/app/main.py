from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, set_request_id_var
from app.db.session import engine
from app.infrastructure.embeddings import get_embedding_provider
from app.db.base import Base
from app.api.router import router as api_router

import app.models  # noqa: register all models

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = get_logger(__name__)


def _ensure_upload_dirs() -> None:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "documents"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "tables"), exist_ok=True)


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    if settings.AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_request_id_var(request_id_var)
    configure_logging()
    logger.info("Starting application")
    
    start = time.time()
    _ensure_upload_dirs()
    await _init_db()
    await asyncio.to_thread(get_embedding_provider)
    app.state.startup_time = round(time.time() - start, 4)
    
    logger.info(f"Application started in {app.state.startup_time}s")
    yield
    logger.info("Application shutting down")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(request_id)
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="DocMind API (async)",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR, check_dir=False), name="uploads")

    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "startup_time_s": getattr(app.state, "startup_time", None)}

    return app


app = create_app()
