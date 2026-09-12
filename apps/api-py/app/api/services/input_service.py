"""Unified Input Processing Service.

Handles multi-format Requirement Documents (PDF, .txt, .md, pasted markdown) and
Implementation Code (Git Diff paste, GitHub PR URL). Performs text extraction,
LLM-backed requirement parsing (for messy, unformatted real-world PRDs), diff noise reduction,
and vector chunking.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.diff_parser import ParsedDiffSummary, parse_unified_diff
from app.core.errors import LLMServiceError
from app.core.extract_text import SourceKindType, extract_text
from app.providers.ai_provider import get_ai_provider

logger = logging.getLogger(__name__)


@dataclass
class ParsedRequirementItem:
    req_id: str  # e.g. R1, R2, C1
    title: str
    description: str
    kind: str = "functional"  # "functional" | "non_functional" | "constraint"
    category: str | None = None


@dataclass
class IngestionResult:
    project_id: str
    source_filename: str
    raw_text_length: int
    requirements: list[ParsedRequirementItem] = field(default_factory=list)
    diff_summary: ParsedDiffSummary | None = None
    chunks_created: int = 0
    token_reduction_percent: float = 0.0


LLM_REQUIREMENT_EXTRACT_SYSTEM_PROMPT = (
    "You are Cartana's Requirements Parsing Engine.\n"
    "Given a raw, unformatted product brief, PRD, or PDF text, extract all actionable product and technical requirements.\n"
    "\n"
    "Rules:\n"
    "1. Ignore marketing intro fluff, conversational background, and team filler.\n"
    "2. Group each requirement into:\n"
    '   - "functional": Features, UI actions, API endpoints, business logic rules.\n'
    '   - "non_functional": Performance targets, security checks, offline behavior, error handling.\n'
    "3. Return ONLY valid JSON in this exact structure:\n"
    "{\n"
    '  "requirements": [\n'
    '    {"id": "R1", "kind": "functional", "category": "UI", "title": "...", "description": "..."},\n'
    '    {"id": "C1", "kind": "non_functional", "category": "Security", "title": "...", "description": "..."}\n'
    "  ]\n"
    "}\n"
    "Output the JSON object only — no markdown code fences, no surrounding text."
)


def parse_requirements_heuristic(raw_text: str) -> list[ParsedRequirementItem]:
    """Fallback heuristic parser if LLM provider is offline or stub mode."""
    lines = raw_text.splitlines()
    items: list[ParsedRequirementItem] = []
    counter = 1
    nf_counter = 1

    for line in lines:
        cleaned = line.strip().lstrip("-*•# ").strip()
        if not cleaned or len(cleaned) < 8:
            continue

        lower = cleaned.lower()
        if any(w in lower for w in ["must", "shall", "should", "required", "needs to", "allow", "support"]):
            if any(w in lower for w in ["performance", "security", "latency", "streaming", "memory", "concurrency", "offline"]):
                req_id = f"C{nf_counter}"
                nf_counter += 1
                kind = "non_functional"
            else:
                req_id = f"R{counter}"
                counter += 1
                kind = "functional"

            title = cleaned[:120]
            items.append(
                ParsedRequirementItem(
                    req_id=req_id,
                    title=title,
                    description=cleaned,
                    kind=kind,
                )
            )

    if not items:
        meaningful = [l.strip() for l in lines if len(l.strip()) > 15]
        for i, line in enumerate(meaningful[:10]):
            items.append(
                ParsedRequirementItem(
                    req_id=f"R{i + 1}",
                    title=line[:120],
                    description=line,
                    kind="functional",
                )
            )

    return items


def extract_requirements_with_llm(raw_text: str) -> list[ParsedRequirementItem]:
    """Extract structured requirements from messy/unformatted PRD text using LLM.

    The ``stub`` provider is the only path that uses the heuristic parser —
    that is an explicit ``LLM_PROVIDER=stub`` configuration, not a failure
    fallback. When a real LLM is configured but fails, we raise instead of
    silently degrading to heuristics.
    """
    ai = get_ai_provider()

    # Explicit "no LLM" mode: use the deterministic heuristic parser directly.
    if getattr(ai, "id", "") == "stub":
        return parse_requirements_heuristic(raw_text)

    if not hasattr(ai, "_structured"):
        raise LLMServiceError(
            "Requirement extraction failed: the configured provider does not "
            "support structured output. Configure an LLM provider or set "
            "LLM_PROVIDER=stub for heuristic extraction."
        )

    try:
        user_prompt = f"SPECIFICATION DOCUMENT TEXT:\n{raw_text[:12000]}"
        raw_json = ai._structured(
            LLM_REQUIREMENT_EXTRACT_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=4096,
            temperature=0.2,
        )
        data = json.loads(raw_json)
        reqs = data.get("requirements", [])
        out: list[ParsedRequirementItem] = []
        for r in reqs:
            out.append(
                ParsedRequirementItem(
                    req_id=str(r.get("id") or f"R{len(out)+1}"),
                    title=str(r.get("title", "")).strip(),
                    description=str(r.get("description", "")).strip(),
                    kind=str(r.get("kind", "functional")),
                    category=str(r.get("category", "")),
                )
            )
        if out:
            return out
    except Exception as exc:
        raise LLMServiceError(
            "Requirement extraction failed: the LLM did not return valid "
            "requirements. Check LLM configuration and try again."
        ) from exc

    raise LLMServiceError(
        "Requirement extraction failed: the LLM returned no requirements."
    )


def process_requirement_file_input(
    file_bytes: bytes, filename: str, file_kind: str = "text", use_llm: bool = True
) -> tuple[str, list[ParsedRequirementItem]]:
    """Extract raw text from PDF/TXT/MD file buffer and parse discrete requirements."""
    kind: SourceKindType = "pdf" if file_kind == "pdf" else "text"
    raw_text = extract_text(file_bytes, kind)
    if use_llm:
        requirements = extract_requirements_with_llm(raw_text)
    else:
        requirements = parse_requirements_heuristic(raw_text)
    return raw_text, requirements


def process_git_diff_input(raw_diff: str) -> ParsedDiffSummary:
    """Noise filter and compress raw git diff (1,000 - 5,000+ lines)."""
    return parse_unified_diff(raw_diff)


def dry_run_pipeline_test(
    req_bytes: bytes | None,
    req_filename: str,
    req_kind: str,
    raw_diff: str | None,
) -> dict[str, Any]:
    """In-Memory Dry-Run test runner for inputs without writing to cloud databases."""
    req_text = ""
    req_items: list[ParsedRequirementItem] = []
    diff_summary: ParsedDiffSummary | None = None

    if req_bytes:
        req_text, req_items = process_requirement_file_input(
            req_bytes, req_filename, req_kind, use_llm=False
        )

    if raw_diff:
        diff_summary = process_git_diff_input(raw_diff)

    raw_diff_len = len(raw_diff) if raw_diff else 0
    compressed_diff_len = len(diff_summary.compressed_text) if diff_summary else 0

    reduction = 0.0
    if raw_diff_len > 0:
        reduction = round((1.0 - (compressed_diff_len / raw_diff_len)) * 100, 1)

    return {
        "requirement_file": req_filename,
        "requirement_text_length": len(req_text),
        "parsed_requirements_count": len(req_items),
        "requirements_preview": [
            {"id": r.req_id, "kind": r.kind, "title": r.title} for r in req_items[:5]
        ],
        "diff_total_files": diff_summary.total_files if diff_summary else 0,
        "diff_kept_files": diff_summary.kept_files if diff_summary else 0,
        "diff_ignored_files": diff_summary.ignored_files if diff_summary else 0,
        "raw_diff_chars": raw_diff_len,
        "compressed_diff_chars": compressed_diff_len,
        "token_reduction_percent": reduction,
    }
