"""Stub task extractor.

Port of ``apps/api/src/ai/extractors/taskExtractor.ts``.

Heuristic-only: scans chunks for sentences that begin with action verbs
(build, create, implement, design, develop, ...) and produces one Task per
match. When possible, links the task to the requirement whose title shares
the most tokens with the task sentence.
"""
from __future__ import annotations

import re

from app.providers.ai_provider import (
    AIExtractTasksInput,
    ExtractedTask,
)

_ACTION_VERBS = [
    "build", "create", "implement", "design", "develop", "add", "test",
    "deploy", "set up", "setup", "configure", "prepare", "generate",
    "write", "document", "integrate", "publish", "submit", "review",
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\n+", " ", text)
    return [s.strip() for s in _SENTENCE_SPLIT.split(cleaned) if len(s.strip()) >= 10]


def _leading_action_verb(sentence: str) -> str | None:
    lower = sentence.lower()
    for verb in _ACTION_VERBS:
        if lower.startswith((verb + " ", verb + ",")):
            return verb
    return None


def _make_title(sentence: str, action: str) -> str:
    cleaned = re.sub(r"\s+", " ", sentence).strip()
    rest = cleaned[len(action):].lstrip(",:").strip()
    title = (action.capitalize() + " " + rest).strip()
    return title[:160] + "\u2026" if len(title) > 160 else title


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [t for t in cleaned.split() if len(t) >= 3]


def _best_requirement_match(
    task_title: str,
    reqs: list[dict[str, str]],
) -> str | None:
    if not reqs:
        return None
    task_tokens = set(_tokenize(task_title))
    best_title: str | None = None
    best_score = 0
    for r in reqs:
        req_tokens = _tokenize(f"{r.get('title', '')} {r.get('description', '')}")
        score = sum(1 for t in req_tokens if t in task_tokens)
        if score > 0 and score > best_score:
            best_score = score
            best_title = r.get("title")
    return best_title


def extract_tasks_stub(input: AIExtractTasksInput) -> list[ExtractedTask]:
    out: list[ExtractedTask] = []
    seen: set[str] = set()

    for chunk in input.chunks:
        text = str(chunk.get("text", ""))
        chunk_id = str(chunk.get("id", ""))
        for sentence in _split_sentences(text):
            action = _leading_action_verb(sentence)
            if not action:
                continue
            title = _make_title(sentence, action)
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            linked = _best_requirement_match(title, input.requirements)
            out.append(ExtractedTask(
                title=title,
                description=sentence.strip(),
                chunkIds=[chunk_id],
                linkedRequirementTitle=linked,
            ))

    return out[:60]

