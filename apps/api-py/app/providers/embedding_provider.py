"""Embedding provider interface and concrete implementations.

Port of ``apps/api/src/ai/EmbeddingProvider.ts``. Two providers: stub
(deterministic FNV-1a hash projected into vector space) and Cloudflare
Workers AI (BGE-base-en-v1.5, 768-dim).

All providers return L2-normalized vectors of dimension ``settings.embedding_dim``.
"""
from __future__ import annotations

import logging
import math
from functools import lru_cache
from typing import Protocol

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Swappable embedding provider interface."""

    id: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


# ---- Helpers ----


def _l2_normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _fnv1a_hash(token: str) -> int:
    h = 2166136261
    for ch in token:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _hash_to_vector(text: str, dim: int) -> list[float]:
    v = [0.0] * dim
    tokens = [t for t in text.lower().split() if t]
    for tok in tokens:
        idx = _fnv1a_hash(tok) % dim
        v[idx] += 1.0
    return _l2_normalize(v)


def to_pg_vector_literal(v: list[float]) -> str:
    """Format a vector for pgvector's literal input: '[v1,v2,...]'."""
    return f"[{','.join(str(x) for x in v)}]"


# ---- Stub provider ----


class StubEmbeddingProvider:
    """Deterministic pseudo-embeddings so the pipeline never crashes in dev."""

    id = "stub"

    @property
    def dim(self) -> int:
        return get_settings().embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        d = self.dim
        return [_hash_to_vector(t, d) for t in texts]


# ---- Cloudflare provider ----


class CloudflareEmbeddingProvider:
    """Cloudflare Workers AI embedding provider (BGE-base-en-v1.5, 768-dim)."""

    id = "cloudflare"

    def __init__(self, account_id: str, api_token: str, model: str) -> None:
        self._url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        self._dim = get_settings().embedding_dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            resp = httpx.post(
                self._url,
                json={"text": text},
                headers=self._headers,
                timeout=60,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Cloudflare embed failed: {resp.status_code} {resp.text}")

            data = resp.json()
            result = data.get("result")
            if isinstance(result, dict) and "data" in result:
                vec = result["data"][0]
            elif isinstance(result, list):
                vec = result
            else:
                raise RuntimeError("Cloudflare embed: unexpected response shape")

            if len(vec) != self._dim:
                raise RuntimeError(f"Embedding dim mismatch: got {len(vec)}, expected {self._dim}")
            results.append(_l2_normalize(vec))
        return results


# ---- Factory ----


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider

    if provider == "cloudflare":
        if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
            logger.warning(
                "EMBEDDING_PROVIDER=cloudflare but credentials missing. Falling back to stub."
            )
            return StubEmbeddingProvider()
        return CloudflareEmbeddingProvider(
            settings.cloudflare_account_id,
            settings.cloudflare_api_token,
            settings.embedding_model,
        )

    return StubEmbeddingProvider()
