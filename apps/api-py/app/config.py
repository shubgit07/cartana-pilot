from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # App
    node_env: str = "development"
    log_level: str = "info"

    # API
    api_port: int = 4000
    api_base_url: str = "http://localhost:4000"

    # Database (same DATABASE_URL as the Node backend; converted for SQLAlchemy below)
    database_url: str = "postgresql://cartana:cartana@localhost:5432/cartana"

    # Redis (ARQ jobs)
    redis_url: str = "redis://localhost:6379"

    # Storage
    storage_driver: Literal["local", "s3"] = "local"
    storage_local_root: str = "./storage"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"
    aws_s3_bucket_name: str | None = None
    aws_s3_endpoint_url: str | None = None

    # Embedding provider (EMBEDDING_DIM is locked at 768 per the agreed schema decision)
    embedding_provider: Literal["stub", "cloudflare"] = "stub"
    embedding_model: str = "@cf/baai/bge-base-en-v1.5"
    embedding_dim: int = 768
    cloudflare_account_id: str | None = None
    cloudflare_api_token: str | None = None

    # Qdrant Cloud (Vector DB)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "cartana_chunks"

    # Upstash Redis REST (for serverless caching and rate limiting)
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None

    # LLM generation provider
    llm_provider: Literal["stub", "fireworks", "groq", "gemini", "cerebras", "routing"] = "stub"
    llm_model: str = "stub"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Cerebras (Ultra-fast inference free tier)
    cerebras_api_key: str | None = None
    cerebras_model: str = "llama3.1-8b"

    # Fireworks (Phase 3 audit LLM)
    fireworks_api_key: str | None = None
    fireworks_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"

    # Groq (LLM_PROVIDER=routing → chat uses the chat model; extraction/audit fall back to Groq)
    groq_api_key: str | None = None
    groq_chat_model: str = "llama-3.3-70b-versatile"
    groq_extract_model: str = "llama-3.1-8b-instant"
    groq_audit_model: str = "llama-3.3-70b-versatile"

    # Gemini (LLM_PROVIDER=routing → structured extraction/audit + chat fallback)
    gemini_api_key: str | None = None
    gemini_chat_model: str = "gemini-3.6-flash"
    gemini_audit_model: str = "gemini-3.5-flash-lite"

    # Cost/compute budgets
    extract_max_chars: int = 80_000
    chat_history_max_messages: int = 12
    embed_concurrency: int = 8
    ingest_timeout_seconds: int = 600

    # Dev user (single-user local MVP, no auth yet)
    dev_user_id: str = "dev-user"
    dev_user_email: str = "dev@cartana.local"
    dev_user_name: str = "Local Dev"

    @property
    def sqlalchemy_database_url(self) -> str:
        """Rewrite the shared postgresql:// URL for the psycopg v3 SQLAlchemy driver.

        Strips legacy Prisma query params (e.g. ``?schema=public``) which
        psycopg rejects with ``invalid connection option "schema"``, while
        preserving driver params Neon/pooled URLs rely on (``sslmode``,
        ``channel_binding``, ...).
        """
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

        scheme, netloc, path, query, fragment = urlsplit(self.database_url)
        if query:
            kept = [(k, v) for k, v in parse_qsl(query) if k.lower() != "schema"]
            query = urlencode(kept)
        url = urlunsplit((scheme, netloc, path, query, fragment))
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
