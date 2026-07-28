from functools import lru_cache
from typing import Literal, Optional

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

    # Redis / Celery
    redis_url: str = "redis://localhost:6379"

    # Storage
    storage_driver: Literal["local"] = "local"
    storage_local_root: str = "./storage"

    # Embedding provider (EMBEDDING_DIM is locked at 768 per the agreed schema decision)
    embedding_provider: Literal["stub", "cloudflare"] = "stub"
    embedding_model: str = "@cf/baai/bge-base-en-v1.5"
    embedding_dim: int = 768
    cloudflare_account_id: Optional[str] = None
    cloudflare_api_token: Optional[str] = None

    # LLM generation provider
    llm_provider: Literal["stub", "cloudflare", "fireworks"] = "stub"
    llm_model: str = "stub"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    cloudflare_llm_model: str = "@cf/meta/llama-3.1-8b-instruct"

    # Fireworks (Phase 3 audit LLM)
    fireworks_api_key: Optional[str] = None
    fireworks_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"

    # Dev user (single-user local MVP, no auth yet)
    dev_user_id: str = "dev-user"
    dev_user_email: str = "dev@cartana.local"
    dev_user_name: str = "Local Dev"

    @property
    def sqlalchemy_database_url(self) -> str:
        """Rewrite the shared postgresql:// URL for the psycopg v3 SQLAlchemy driver."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
