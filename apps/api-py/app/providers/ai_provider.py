"""AI provider interface and concrete implementations.

Port of ``apps/api/src/ai/AIProvider.ts``. Three providers share the same
interface so swapping is a single config change: stub (heuristic), Cloudflare
Workers AI, and Fireworks AI (OpenAI-compatible, JSON mode for audit).

All providers return the same data shapes so the service layer is agnostic.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Protocol

import httpx

from app.config import Settings, get_settings
from app.providers.extractors.coverage_stub import coverage_stub
from app.providers.extractors.requirement_extractor import extract_requirements_stub
from app.providers.extractors.task_extractor import extract_tasks_stub
from app.providers.prompts.audit import build_coverage_prompt, build_risk_summary_prompt

logger = logging.getLogger(__name__)


# ---- Data shapes (mirror the TS interfaces in AIProvider.ts) ----


@dataclass
class ChatPassage:
    chunkId: str
    sourceId: str
    filename: str
    text: str
    score: float


@dataclass
class ChatCitation:
    sourceId: str
    filename: str
    chunkId: str
    snippet: str
    score: float


@dataclass
class AIChatInput:
    question: str
    history: list[dict[str, str]] = field(default_factory=list)
    passages: list[ChatPassage] = field(default_factory=list)


@dataclass
class AIChatOutput:
    answer: str
    citations: list[ChatCitation]


@dataclass
class ExtractedRequirement:
    title: str
    description: str
    chunkIds: list[str]


@dataclass
class ExtractedTask:
    title: str
    description: str
    chunkIds: list[str]
    linkedRequirementTitle: Optional[str] = None


@dataclass
class AIExtractRequirementsInput:
    sourceFilename: str
    chunks: list[dict[str, object]]


@dataclass
class AIExtractTasksInput:
    sourceFilename: str
    chunks: list[dict[str, object]]
    requirements: list[dict[str, str]]


@dataclass
class CoverageJudgment:
    status: str
    rationale: str


@dataclass
class AIAuditCoverageInput:
    requirement: dict[str, str]
    candidateTasks: list[dict[str, str]]


@dataclass
class AIAuditCoverageOutput:
    judgments: list[CoverageJudgment]


@dataclass
class AIRiskSummaryInput:
    requirements: list[dict[str, str]]
    findings: list[dict[str, str]]


@dataclass
class AIRiskSummaryOutput:
    summary: str


# ---- Provider interface ----


class AIProvider(Protocol):
    """Swappable LLM generation provider interface."""

    id: str

    def chat(self, input: AIChatInput) -> AIChatOutput: ...

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]: ...

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]: ...

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput: ...

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput: ...


# ---- Helpers ----


def _build_citations(passages: list[ChatPassage]) -> list[ChatCitation]:
    return [
        ChatCitation(
            sourceId=p.sourceId,
            filename=p.filename,
            chunkId=p.chunkId,
            snippet=p.text[:240] + "\u2026" if len(p.text) > 240 else p.text,
            score=p.score,
        )
        for p in passages
    ]


def _build_system_prompt(input: AIChatInput) -> str:
    ctx = "\n\n".join(
        f"[{i + 1}] ({p.filename}) {p.text}" for i, p in enumerate(input.passages[:8])
    )
    return "\n".join([
        "You are Cartana, a project specification copilot.",
        "Answer the user's question using ONLY the passages below.",
        "If the answer is not in the passages, say so clearly.",
        "Cite passages inline as [n] and refer to filenames when relevant.",
        "Be concise.",
        "",
        "--- PASSAGES ---",
        ctx,
    ])


def _normalize_status(s: Optional[str]) -> str:
    valid = {"covered", "partial", "unclear", "missing"}
    return s if s in valid else "unclear"


# ---- Stub provider ----


class StubAIProvider:
    """Retrieval-only, heuristic-based. Works end-to-end without an LLM."""

    id = "stub"

    def chat(self, input: AIChatInput) -> AIChatOutput:
        citations = _build_citations(input.passages)
        summary = "\n\n".join(
            f"({i + 1}) {c.snippet}" for i, c in enumerate(citations[:3])
        )
        if citations:
            answer = (
                "Based on the uploaded project material, here is what I found "
                f"that looks relevant to your question:\n\n{summary}\n\n"
                "(See citations below. No live LLM is configured yet — "
                "answers are retrieval-only.)"
            )
        else:
            answer = (
                "I could not find any passages in the uploaded material that "
                "match your question. Try rephrasing, or upload more sources."
            )
        return AIChatOutput(answer=answer, citations=citations)

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        return extract_requirements_stub(input)

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        return extract_tasks_stub(input)

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        return coverage_stub(input)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        total = len(input.requirements)
        covered = sum(1 for r in input.requirements if r["status"] == "covered")
        missing = sum(1 for r in input.requirements if r["status"] == "missing")
        partial = sum(1 for r in input.requirements if r["status"] == "partial")
        critical = sum(1 for f in input.findings if f["severity"] == "critical")

        parts: list[str] = []
        parts.append(f"Coverage audit complete. {covered}/{total} requirements are fully covered.")
        if partial > 0:
            parts.append(f"{partial} requirement{'s' if partial != 1 else ''} have partial coverage.")
        if missing > 0:
            parts.append(f"{missing} requirement{'s' if missing != 1 else ''} are not covered by any task.")
        if critical > 0:
            parts.append(f"{critical} critical finding{'s' if critical != 1 else ''} require attention.")

        return AIRiskSummaryOutput(summary=" ".join(parts))


# ---- Cloudflare provider ----


class CloudflareAIProvider:
    """Cloudflare Workers AI generation provider."""

    id = "cloudflare"

    def __init__(self, account_id: str, api_token: str, model: str) -> None:
        self._model = model
        self._url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def chat(self, input: AIChatInput) -> AIChatOutput:
        sys_prompt = _build_system_prompt(input)
        messages = [{"role": "system", "content": sys_prompt}]
        for m in input.history:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": input.question})

        resp = httpx.post(self._url, json={"messages": messages}, headers=self._headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Cloudflare LLM failed: {resp.status_code} {resp.text}")

        data = resp.json()
        result = data.get("result")
        if isinstance(result, str):
            answer = result
        elif isinstance(result, dict):
            answer = result.get("response", "")
        else:
            answer = ""

        return AIChatOutput(answer=answer, citations=_build_citations(input.passages))

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        return extract_requirements_stub(input)

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        return extract_tasks_stub(input)

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        return coverage_stub(input)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        total = len(input.requirements)
        covered = sum(1 for r in input.requirements if r["status"] == "covered")
        missing = sum(1 for r in input.requirements if r["status"] == "missing")
        summary = f"Coverage: {covered}/{total} fully covered, {missing} missing. {len(input.findings)} findings."
        return AIRiskSummaryOutput(summary=summary)


# ---- Fireworks provider ----


class FireworksAIProvider:
    """Fireworks AI — OpenAI-compatible chat completions with JSON mode."""

    id = "fireworks"
    _url = "https://api.fireworks.ai/inference/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, input: AIChatInput) -> AIChatOutput:
        sys_prompt = _build_system_prompt(input)
        messages = [{"role": "system", "content": sys_prompt}]
        for m in input.history:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": input.question})

        body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.3,
        }
        resp = httpx.post(self._url, json=body, headers=self._headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Fireworks LLM failed: {resp.status_code} {resp.text}")

        choices = resp.json().get("choices", [])
        answer = choices[0]["message"]["content"] if choices else ""
        return AIChatOutput(answer=answer, citations=_build_citations(input.passages))

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        return extract_requirements_stub(input)

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        return extract_tasks_stub(input)

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        system_prompt, user_prompt = build_coverage_prompt(input)
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 2048,
            "temperature": 0.2,
        }
        resp = httpx.post(self._url, json=body, headers=self._headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Fireworks audit failed: {resp.status_code} {resp.text}")

        choices = resp.json().get("choices", [])
        raw = choices[0]["message"]["content"] if choices else "{}"

        try:
            parsed = json.loads(raw)
            judgments = [
                CoverageJudgment(
                    status=_normalize_status(j.get("status")),
                    rationale=j.get("rationale", ""),
                )
                for j in parsed.get("judgments", [])
            ]
            return AIAuditCoverageOutput(judgments=judgments)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Fireworks audit returned invalid JSON — falling back to stub")
            return coverage_stub(input)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        prompt = build_risk_summary_prompt(input)
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": "You are a project risk analyst. Be concise."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        resp = httpx.post(self._url, json=body, headers=self._headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Fireworks risk summary failed: {resp.status_code} {resp.text}")

        choices = resp.json().get("choices", [])
        summary = choices[0]["message"]["content"] if choices else ""
        return AIRiskSummaryOutput(summary=summary)


# ---- Factory ----


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "cloudflare":
        if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
            logger.warning("LLM_PROVIDER=cloudflare but credentials missing. Using stub.")
            return StubAIProvider()
        return CloudflareAIProvider(
            settings.cloudflare_account_id,
            settings.cloudflare_api_token,
            settings.cloudflare_llm_model,
        )

    if provider == "fireworks":
        if not settings.fireworks_api_key:
            logger.warning("LLM_PROVIDER=fireworks but FIREWORKS_API_KEY missing. Using stub.")
            return StubAIProvider()
        return FireworksAIProvider(settings.fireworks_api_key, settings.fireworks_model)

    return StubAIProvider()
