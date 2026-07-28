"""Deterministic dedupe key — sha256(sourceId + normalized title).

Port of ``apps/api/src/lib/dedupe.ts``. Used for idempotent re-extraction.
"""
from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")


def dedupe_key(source_id: str, title: str) -> str:
    norm = _WS.sub(" ", title.strip().lower())
    return hashlib.sha256(f"{source_id}|{norm}".encode("utf-8")).hexdigest()
