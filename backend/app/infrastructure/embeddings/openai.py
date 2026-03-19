from __future__ import annotations

from app.core.config import settings
from .base import EmbeddingProvider

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for EMBEDDING_PROVIDER=openai")
        from openai import OpenAI  # type: ignore
        self.client = OpenAI(base_url=settings.OPENAI_BASE_URL,api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]

    def embed_one(self, text: str) -> list[float]:
        return self.embed_many([text])[0]
