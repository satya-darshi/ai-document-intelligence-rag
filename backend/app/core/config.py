from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI Document Intelligence & RAG Platform"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://raguser:ragpassword@localhost:5432/ragdb"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "document_chunks"

    # Cloud free-tier AI stack. The application itself remains local in Docker.
    # Do not configure a paid/billed Gemini project if you want to keep this project at ₹0.
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-2"
    embedding_dimension: int = 768
    embedding_batch_size: int = 8
    llm_thinking_budget: int = 512

    chunk_size: int = 900
    chunk_overlap: int = 120
    top_k: int = 8
    rerank_top_k: int = 5
    cache_ttl_seconds: int = 300
    max_upload_mb: int = 20

    upload_dir: str = "data/uploads"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
