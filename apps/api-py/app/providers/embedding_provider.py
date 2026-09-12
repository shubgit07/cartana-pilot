"""Embedding provider interface and concrete implementations.

Port of ``apps/api/src/ai/EmbeddingProvider.ts``. Two providers: stub
(deterministic FNV-1a hash projected into vector space) and Cloudflare
Workers AI (BGE-base-en-v1.5, 768-dim).

All providers return L2-normalized vectors of dimension ``settings.embedding_dim``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Protocol

import httpx
import redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Swappable embedding provider interface (identity members are read-only)."""

    @property
    def id(self) -> str: ...

    @property
    def dim(self) -> int: ...

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
        concurrency = get_settings().embed_concurrency
        if len(texts) <= 1 or concurrency <= 1:
            return [self._embed_one(t) for t in texts]
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            return list(pool.map(self._embed_one, texts))

    def _embed_one(self, text: str) -> list[float]:
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
        return _l2_normalize(vec)


# ---- Embedding cache (Redis) ----

def _embedding_key(text: str) -> str:
    return f"embed:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class EmbeddingCache:
    """Redis cache keyed by content hash. Raises if Redis is unavailable at init."""

    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=2)
        self._redis.ping()

    def get(self, key: str) -> list[float] | None:
        try:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None
        except (redis.RedisError, json.JSONDecodeError, TypeError):
            return None

    def set(self, key: str, value: list[float]) -> None:
        try:
            self._redis.set(key, json.dumps(value))
        except redis.RedisError:
            pass


class CachedEmbeddingProvider:
    """Wraps a real provider; unchanged text reuses cached vectors instead of re-embedding."""

    def __init__(self, provider: EmbeddingProvider, cache: EmbeddingCache) -> None:
        self._provider = provider
        self._cache = cache

    @property
    def id(self) -> str:
        return self._provider.id

    @property
    def dim(self) -> int:
        return self._provider.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        keys = [_embedding_key(t) for t in texts]
        hits = {
            k: v for k, v in zip(keys, [self._cache.get(k) for k in keys]) if v is not None
        }
        misses = [t for i, t in enumerate(texts) if keys[i] not in hits]
        vectors = self._provider.embed(misses) if misses else []
        miss_iter = iter(vectors)

        result: list[list[float]] = []
        for key, text in zip(keys, texts):
            if key in hits:
                result.append(hits[key])
            else:
                vec = next(miss_iter)
                self._cache.set(key, vec)
                result.append(vec)
        return result


def _maybe_cached(provider: EmbeddingProvider) -> EmbeddingProvider:
    try:
        cache = EmbeddingCache(get_settings().redis_url)
        return CachedEmbeddingProvider(provider, cache)
    except Exception:  # noqa: BLE001
        logger.warning("Redis unavailable — embedding cache disabled")
        return provider


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
        return _maybe_cached(
            CloudflareEmbeddingProvider(
                settings.cloudflare_account_id,
                settings.cloudflare_api_token,
                settings.embedding_model,
            )
        )

    return StubEmbeddingProvider()
