from __future__ import annotations
from abc import ABC, abstractmethod

from app.core.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_one(self, text: str) -> list[float]:
        raise NotImplementedError

_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        p = (settings.EMBEDDING_PROVIDER or "").lower().strip()
        if p == "openai":
            from .openai import OpenAIEmbeddingProvider
            _provider = OpenAIEmbeddingProvider()
        else:
            from .sbert import SBERTEmbeddingProvider
            _provider = SBERTEmbeddingProvider()
    return _provider
