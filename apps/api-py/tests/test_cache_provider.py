"""Unit tests for Upstash Redis REST & Memory Cache Provider.

Tests audit result caching by sha256(spec + diff) and rate limiting.
"""
from __future__ import annotations

from app.providers.cache_provider import (
    _MEMORY_CACHE,
    cache_audit,
    check_rate_limit,
    get_cached_audit,
)


def test_memory_cache_fallback():
    spec_hash = "spec_12345"
    diff_hash = "diff_abcde"
    mock_brief = {
        "id": "brief-1",
        "projectId": "proj-1",
        "title": "PR Trust Brief",
        "coverageScore": 90,
        "trustLevel": "high",
        "summary": "High trust PR",
    }

    # Ensure clean state
    key = f"audit:cache:{spec_hash}:{diff_hash}"
    _MEMORY_CACHE.pop(key, None)

    # 1. First fetch should return None
    cached = get_cached_audit(spec_hash, diff_hash)
    assert cached is None

    # 2. Cache output
    cache_audit(spec_hash, diff_hash, mock_brief, ttl_seconds=3600)

    # 3. Subsequent fetch should return the cached dict
    cached_again = get_cached_audit(spec_hash, diff_hash)
    assert cached_again is not None
    assert cached_again["id"] == "brief-1"
    assert cached_again["coverageScore"] == 90


def test_check_rate_limit_sliding_window():
    user_id = "user_test_rate_limit"
    rate_key_prefix = f"ratelimit:{user_id}:"
    # Ensure clean state (any prior runs in the same minute)
    for key in list(_MEMORY_CACHE):
        if key.startswith(rate_key_prefix):
            _MEMORY_CACHE.pop(key, None)

    # Under limit (max_rpm = 2): first two calls allowed
    assert check_rate_limit(user_id, max_rpm=2) is True
    assert check_rate_limit(user_id, max_rpm=2) is True

    # Over limit: third call in the same minute rejected
    assert check_rate_limit(user_id, max_rpm=2) is False
