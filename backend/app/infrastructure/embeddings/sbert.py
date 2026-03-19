from __future__ import annotations

from app.core.config import settings
from .base import EmbeddingProvider

class SBERTEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        self.model = SentenceTransformer(settings.SBERT_MODEL)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        vecs = self.model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
        
    def embed_one(self, text: str) -> list[float]:
        return self.embed_many([text])[0]