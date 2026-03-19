from __future__ import annotations

import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "DocMind API"
    AUTO_CREATE_TABLES: bool = True
    UPLOAD_DIR: str = "uploads"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    EMBEDDING_PROVIDER: str = "sbert"  # openai | sbert
    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_BASE_URL: str | None = None
    SBERT_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384  # MiniLM-L6-v2 default dimension

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Query Rewrite
    QUERY_REWRITE_ENABLED: bool = False

    # Answer Aggregation
    ANSWER_MAX_CHUNKS: int = 5

    SESSION_TTL_SECONDS: int = 86400

    class Config:
        env_file = ".env"
        case_sensitive = True

    @staticmethod
    def _parse_json_list(value: str) -> list[str]:
        try:
            v = json.loads(value)
            return v if isinstance(v, list) else []
        except Exception:
            return []

    def model_post_init(self, __context):
        if isinstance(self.CORS_ORIGINS, str):
            self.CORS_ORIGINS = self._parse_json_list(self.CORS_ORIGINS)


settings = Settings()
