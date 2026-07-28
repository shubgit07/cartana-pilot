"""Tests for the dedupe key helper.

Port of ``apps/api/src/lib/dedupe.test.ts``.
"""
from __future__ import annotations

from app.core.dedupe import dedupe_key


def test_dedupe_key_is_deterministic():
    k1 = dedupe_key("src-1", "Must support SSO")
    k2 = dedupe_key("src-1", "Must support SSO")
    assert k1 == k2


def test_dedupe_key_differs_by_source():
    k1 = dedupe_key("src-1", "Must support SSO")
    k2 = dedupe_key("src-2", "Must support SSO")
    assert k1 != k2


def test_dedupe_key_differs_by_title():
    k1 = dedupe_key("src-1", "Must support SSO")
    k2 = dedupe_key("src-1", "Must support logging")
    assert k1 != k2


def test_dedupe_key_normalizes_whitespace():
    k1 = dedupe_key("src-1", "Must   support   SSO")
    k2 = dedupe_key("src-1", "Must support SSO")
    assert k1 == k2


def test_dedupe_key_normalizes_case():
    k1 = dedupe_key("src-1", "Must Support SSO")
    k2 = dedupe_key("src-1", "must support sso")
    assert k1 == k2


def test_dedupe_key_is_hex_string():
    k = dedupe_key("src-1", "test")
    assert len(k) == 64
    int(k, 16)
