from __future__ import annotations

import os
import uuid
from typing import Optional

import aiofiles
from starlette.concurrency import run_in_threadpool

from app.core.config import settings


class LocalFileStorage:
    async def ensure_dirs(self) -> None:
        await run_in_threadpool(os.makedirs, settings.UPLOAD_DIR, exist_ok=True)
        await run_in_threadpool(
            os.makedirs,
            os.path.join(settings.UPLOAD_DIR, "documents"),
            exist_ok=True
        )
        await run_in_threadpool(
            os.makedirs,
            os.path.join(settings.UPLOAD_DIR, "images"),
            exist_ok=True
        )
        await run_in_threadpool(
            os.makedirs,
            os.path.join(settings.UPLOAD_DIR, "tables"),
            exist_ok=True
        )

    async def save_bytes(self, subdir: str, filename: str, content: bytes) -> str:
        await self.ensure_dirs()
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        path = os.path.join(settings.UPLOAD_DIR, subdir, safe_name)
        
        async with aiofiles.open(path, "wb") as f:
            await f.write(content)
        
        return path

    async def exists(self, path: str) -> bool:
        return await run_in_threadpool(os.path.exists, path)

    async def remove(self, path: str) -> None:
        exists = await self.exists(path)
        if exists:
            await run_in_threadpool(os.remove, path)
