"""Cache and rate-limiting provider using Upstash Redis REST or in-memory fallback.

Inspired by the reference architecture: provides zero-connection-overhead REST
caching for embeddings, sliding-window rate limiting for free-tier LLM protection,
and audit result deduplication so repeated PR evaluations cost 0 LLM tokens.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# In-memory fallback cache when Upstash Redis is not configured
_MEMORY_CACHE: dict[str, tuple[Any, float]] = {}


def _get_upstash_config() -> tuple[str | None, str | None]:
    settings = get_settings()
    url = settings.upstash_redis_rest_url
    token = settings.upstash_redis_rest_token
    if url and token:
        return url.rstrip("/"), token
    return None, None


def redis_get(key: str) -> Any | None:
    """Retrieve a value from Upstash Redis REST or in-memory cache."""
    url, token = _get_upstash_config()
    if url and token:
        encoded_key = urllib.parse.quote(key, safe="")
        endpoint = f"{url}/get/{encoded_key}"
        try:
            resp = httpx.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
                timeout=4.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result")
                if result is not None:
                    if isinstance(result, str):
                        try:
                            return json.loads(result)
                        except json.JSONDecodeError:
                            return result
                    return result
        except Exception as e:  # noqa: BLE001
            logger.debug("Upstash Redis get error for key %s: %s", key, e)

    # In-memory fallback
    entry = _MEMORY_CACHE.get(key)
    if entry:
        val, expiry = entry
        if expiry == 0 or expiry > time.time():
            return val
        del _MEMORY_CACHE[key]
    return None


def redis_set(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Store a value in Upstash Redis REST or in-memory cache."""
    serialized = value if isinstance(value, str) else json.dumps(value)
    url, token = _get_upstash_config()

    if url and token:
        encoded_key = urllib.parse.quote(key, safe="")
        encoded_val = urllib.parse.quote(serialized, safe="")
        endpoint = f"{url}/set/{encoded_key}/{encoded_val}?ex={ttl_seconds}"
        try:
            resp = httpx.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
                timeout=4.0,
            )
            if resp.status_code == 200:
                return True
        except Exception as e:  # noqa: BLE001
            logger.debug("Upstash Redis set error for key %s: %s", key, e)

    # In-memory fallback
    expiry = time.time() + ttl_seconds if ttl_seconds > 0 else 0
    _MEMORY_CACHE[key] = (value, expiry)
    return True


def redis_del(key: str) -> bool:
    """Delete a key from Upstash Redis REST or in-memory cache."""
    url, token = _get_upstash_config()
    if url and token:
        encoded_key = urllib.parse.quote(key, safe="")
        endpoint = f"{url}/del/{encoded_key}"
        try:
            resp = httpx.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
                timeout=4.0,
            )
            if resp.status_code == 200:
                return True
        except Exception as e:  # noqa: BLE001
            logger.debug("Upstash Redis del error for key %s: %s", key, e)

    _MEMORY_CACHE.pop(key, None)
    return True


def check_rate_limit(user_id: str, max_rpm: int = 20) -> bool:
    """Sliding-window rate limiter per user/minute to protect free-tier LLMs.

    Returns True if request is allowed, False if limit exceeded.
    """
    current_minute = int(time.time() // 60)
    rate_key = f"ratelimit:{user_id}:{current_minute}"
    current_count = redis_get(rate_key) or 0

    if int(current_count) >= max_rpm:
        return False

    redis_set(rate_key, int(current_count) + 1, ttl_seconds=60)
    return True


def get_cached_audit(spec_hash: str, diff_hash: str) -> dict[str, Any] | None:
    """Fetch previously computed PR audit result by hashes to save LLM tokens."""
    cache_key = f"audit:cache:{spec_hash}:{diff_hash}"
    cached = redis_get(cache_key)
    if isinstance(cached, dict):
        return cached
    return None


def cache_audit(
    spec_hash: str, diff_hash: str, result: dict[str, Any], ttl_seconds: int = 86400
) -> None:
    """Cache PR audit result for 24h to avoid redundant LLM invocations."""
    cache_key = f"audit:cache:{spec_hash}:{diff_hash}"
    redis_set(cache_key, result, ttl_seconds=ttl_seconds)
