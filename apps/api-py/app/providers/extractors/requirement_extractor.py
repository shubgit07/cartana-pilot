"""Stub requirement extractor.

Port of ``apps/api/src/ai/extractors/requirementExtractor.ts``.

Heuristic-only: scans chunks for sentences that read like project requirements
(contain "must", "should", "required", "needs to", "has to", "shall") and
produces one Requirement per match. Quality is mediocre by design — the point
is that the pipeline works end-to-end without an LLM configured.
"""
from __future__ import annotations

import re

from app.providers.ai_provider import (
    AIExtractRequirementsInput,
    ExtractedRequirement,
)

_REQUIREMENT_KEYWORDS = [
    re.compile(r"\bmust\b", re.IGNORECASE),
    re.compile(r"\bshall\b", re.IGNORECASE),
    re.compile(r"\bshould\b", re.IGNORECASE),
    re.compile(r"\bneeds to\b", re.IGNORECASE),
    re.compile(r"\bhas to\b", re.IGNORECASE),
    re.compile(r"\bis required\b", re.IGNORECASE),
    re.compile(r"\bare required\b", re.IGNORECASE),
    re.compile(r"\brequired to\b", re.IGNORECASE),
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\n+", " ", text)
    return [s.strip() for s in _SENTENCE_SPLIT.split(cleaned) if len(s.strip()) >= 12]


def _looks_like_requirement(sentence: str) -> bool:
    if len(sentence) > 320:
        return False
    return any(pat.search(sentence) for pat in _REQUIREMENT_KEYWORDS)


def _make_title(sentence: str) -> str:
    cleaned = re.sub(r"\s+", " ", sentence).strip()
    title = cleaned[:120]
    if not title.endswith(".") and len(title) == 120:
        title += "\u2026"
    return title


def extract_requirements_stub(input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
    out: list[ExtractedRequirement] = []
    seen: set[str] = set()

    for chunk in input.chunks:
        text = str(chunk.get("text", ""))
        chunk_id = str(chunk.get("id", ""))
        for sentence in _split_sentences(text):
            if not _looks_like_requirement(sentence):
                continue
            title = _make_title(sentence)
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            out.append(ExtractedRequirement(
                title=title,
                description=sentence.strip(),
                chunkIds=[chunk_id],
            ))

    return out[:40]
