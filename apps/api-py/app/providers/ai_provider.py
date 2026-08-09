"""AI provider interface and concrete implementations.

Port of ``apps/api/src/ai/AIProvider.ts``. A single interface across concrete
providers — stub (heuristic), Fireworks, Groq, Cerebras and Gemini — so
swapping is a single config change.

All providers return the same data shapes so the service layer is agnostic.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

import httpx

from app.config import get_settings

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
    linkedRequirementTitle: str | None = None


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

    def _structured(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str: ...

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
    return (
        "You are Cartana, a project specification copilot.\n"
        "Answer the user's question using ONLY the passages below.\n"
        "If the answer is not in the passages, say so clearly.\n"
        "Cite passages inline as [n] and refer to filenames when relevant.\n"
        "Be concise.\n"
        "\n"
        "--- PASSAGES ---\n"
        f"{ctx}"
    )


def _normalize_status(s: str | None) -> str:
    valid = {"covered", "partial", "unclear", "missing"}
    return s if s in valid else "unclear"


def _parse_retry_after(message: str) -> float:
    """Extract a wait time (seconds) from a 429 error message.

    Groq messages look like ``... Try again in 41.66s. ...``. Defaults to a
    conservative 15s backoff if no delay is present.
    """
    match = re.search(r"again in ([\d.]+)s", message)
    return float(match.group(1)) if match else 15.0


def _is_retryable(exc: Exception) -> bool:
    """Whether a provider failure is safe to retry via a fallback chain.

    Retryable: HTTP/transport errors, rate limits (429), provider error codes
    (e.g. 5035), 5xx server errors, invalid structured JSON (the fallback
    provider may produce valid output), and timeouts.
    Non-retryable: 4xx schema/validation errors (the request itself is bad).
    """
    if isinstance(exc, httpx.HTTPError):
        return True
    text = str(exc)
    return (
        "429" in text
        or "5035" in text
        or bool(re.search(r"\b(?:500|502|503|504|520|521|522|523|524)\b", text))
        or bool(re.search(r"invalid json", text, re.IGNORECASE))
        or bool(re.search(r"timeout|timed out", text, re.IGNORECASE))
    )


def _safe_json_loads(raw: object, *, label: str) -> object:
    """Parse an LLM JSON response defensively.

    Providers may return the response either as an already parsed JSON object
    (dict) or as a raw string. For strings, models sometimes
    wrap JSON in markdown fences or append prose even in JSON mode: strip
    fences, isolate the outermost JSON value, and retry. On failure log a
    snippet of the raw response for diagnosis and raise.
    """
    if isinstance(raw, dict):
        return raw
    candidate = str(raw).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                pass
        snippet = candidate[:200]
        tail = candidate[-200:]
        logger.warning(
            "%s returned unparseable JSON. Raw head: %r | tail: %r",
            label,
            snippet,
            tail,
        )
        raise RuntimeError(f"{label} returned invalid JSON") from None


# ---- Stub provider ----

from app.providers.extractors.coverage_stub import coverage_stub
from app.providers.extractors.requirement_extractor import extract_requirements_stub
from app.providers.extractors.task_extractor import extract_tasks_stub
from app.providers.prompts.audit import build_coverage_prompt, build_risk_summary_prompt
from app.providers.prompts.extraction import (
    build_extract_requirements_prompt,
    build_extract_tasks_prompt,
)


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

    def _structured(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str:
        """Structured (JSON) generation requires a real LLM.

        The stub provider is retrieval-only and has no LLM, so it must fail
        loudly instead of emitting fabricated structured output.
        """
        raise RuntimeError(
            "LLM_PROVIDER=stub has no LLM: structured output is unavailable. "
            "Configure a real LLM provider (e.g. LLM_PROVIDER=routing)."
        )

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

    def _structured(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = httpx.post(self._url, json=body, headers=self._headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Fireworks LLM failed: {resp.status_code} {resp.text}")

        choices = resp.json().get("choices", [])
        return choices[0]["message"]["content"] if choices else ""

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


# ---- Groq provider ----

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAIProvider:
    """Groq — OpenAI-compatible chat completions with JSON mode for structured tasks."""

    id = "groq"
    _url = GROQ_URL

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, body: dict[str, object]) -> str:
        resp = httpx.post(self._url, json=body, headers=self._headers, timeout=90)
        if resp.status_code != 200:
            raise RuntimeError(f"Groq LLM failed: {resp.status_code} {resp.text}")
        choices = resp.json().get("choices", [])
        return choices[0]["message"]["content"] if choices else ""

    def _post_with_retry(self, body: dict[str, object], *, attempts: int = 3) -> str:
        """POST with bounded retry on rate limits (429)."""
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return self._post(body)
            except RuntimeError as exc:
                if "429" not in str(exc) or attempt == attempts - 1:
                    raise
                wait = _parse_retry_after(str(exc))
                logger.warning(
                    "Groq rate limited (attempt %d/%d) — retrying in %.1fs",
                    attempt + 1,
                    attempts,
                    wait,
                )
                time.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"Groq LLM failed after {attempts} attempts: {last_exc}")

    def _structured(
        self, system: str, user: str, *, max_tokens: int, temperature: float
    ) -> str:
        return self._post_with_retry({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": temperature,
        })

    def chat(self, input: AIChatInput) -> AIChatOutput:
        messages = [{"role": "system", "content": _build_system_prompt(input)}]
        for m in input.history:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": input.question})

        answer = self._post_with_retry({
            "model": self._model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.3,
        })
        return AIChatOutput(answer=answer, citations=_build_citations(input.passages))

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        system, user = build_extract_requirements_prompt(input)
        chunk_ids = [str(c.get("id", "")) for c in input.chunks]

        try:
            parsed = json.loads(self._structured(system, user, max_tokens=2048, temperature=0.2))
            items = parsed.get("requirements", [])
        except json.JSONDecodeError:
            logger.warning("Groq requirements extraction returned invalid JSON — using stub")
            return extract_requirements_stub(input)

        out: list[ExtractedRequirement] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            idxs = item.get("chunkIndexes") or []
            ids = [
                chunk_ids[i - 1]
                for i in idxs
                if isinstance(i, int) and 1 <= i <= len(chunk_ids)
            ]
            if not ids and chunk_ids:
                ids = [chunk_ids[0]]
            out.append(ExtractedRequirement(
                title=title,
                description=str(item.get("description", "")).strip(),
                chunkIds=ids,
            ))
        return out

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        system, user = build_extract_tasks_prompt(input)
        chunk_ids = [str(c.get("id", "")) for c in input.chunks]

        try:
            parsed = json.loads(self._structured(system, user, max_tokens=2048, temperature=0.2))
            items = parsed.get("tasks", [])
        except json.JSONDecodeError:
            logger.warning("Groq tasks extraction returned invalid JSON — using stub")
            return extract_tasks_stub(input)

        out: list[ExtractedTask] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            idxs = item.get("chunkIndexes") or []
            ids = [
                chunk_ids[i - 1]
                for i in idxs
                if isinstance(i, int) and 1 <= i <= len(chunk_ids)
            ]
            if not ids and chunk_ids:
                ids = [chunk_ids[0]]
            linked = item.get("linkedRequirementTitle")
            out.append(ExtractedTask(
                title=title,
                description=str(item.get("description", "")).strip(),
                chunkIds=ids,
                linkedRequirementTitle=str(linked) if linked else None,
            ))
        return out

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        system_prompt, user_prompt = build_coverage_prompt(input)
        raw = self._structured(system_prompt, user_prompt, max_tokens=1024, temperature=0.2)

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
            logger.warning("Groq audit returned invalid JSON — falling back to stub")
            return coverage_stub(input)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        answer = self._post_with_retry({
            "model": self._model,
            "messages": [
                {"role": "system", "content": "You are a project risk analyst. Be concise."},
                {"role": "user", "content": build_risk_summary_prompt(input)},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        })
        return AIRiskSummaryOutput(summary=answer)


# ---- Cerebras provider ----

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"


class CerebrasAIProvider:
    """Cerebras — Ultra-fast OpenAI-compatible inference with JSON mode support."""

    id = "cerebras"
    parallel_audit = True
    _url = CEREBRAS_URL

    def __init__(self, api_key: str, model: str = "llama3.1-8b") -> None:
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, body: dict[str, object]) -> str:
        resp = httpx.post(self._url, json=body, headers=self._headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Cerebras LLM failed: {resp.status_code} {resp.text}")
        choices = resp.json().get("choices", [])
        return choices[0]["message"]["content"] if choices else ""

    def _post_with_retry(self, body: dict[str, object], *, attempts: int = 3) -> str:
        """POST with bounded retry on rate limits (429) and transient errors."""
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return self._post(body)
            except RuntimeError as exc:
                if "429" not in str(exc) or attempt == attempts - 1:
                    raise
                wait = _parse_retry_after(str(exc))
                logger.warning(
                    "Cerebras rate limited (attempt %d/%d) — retrying in %.1fs",
                    attempt + 1,
                    attempts,
                    wait,
                )
                time.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"Cerebras LLM failed after {attempts} attempts: {last_exc}")

    def _structured(
        self, system: str, user: str, *, max_tokens: int = 2048, temperature: float = 0.2
    ) -> str:
        return self._post_with_retry({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": temperature,
        })

    def chat(self, input: AIChatInput) -> AIChatOutput:
        messages = [{"role": "system", "content": _build_system_prompt(input)}]
        for m in input.history:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": input.question})

        answer = self._post_with_retry({
            "model": self._model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.3,
        })
        return AIChatOutput(answer=answer, citations=_build_citations(input.passages))

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        system, user = build_extract_requirements_prompt(input)
        chunk_ids = [str(c.get("id", "")) for c in input.chunks]

        parsed = _safe_json_loads(
            self._structured(system, user, max_tokens=4096, temperature=0.2),
            label="Cerebras requirements extraction",
        )
        items = parsed.get("requirements", []) if isinstance(parsed, dict) else []

        out: list[ExtractedRequirement] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            idxs = item.get("chunkIndexes") or []
            ids = [
                chunk_ids[i - 1]
                for i in idxs
                if isinstance(i, int) and 1 <= i <= len(chunk_ids)
            ]
            if not ids and chunk_ids:
                ids = [chunk_ids[0]]
            out.append(ExtractedRequirement(
                title=title,
                description=str(item.get("description", "")).strip(),
                chunkIds=ids,
            ))
        return out

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        system, user = build_extract_tasks_prompt(input)
        chunk_ids = [str(c.get("id", "")) for c in input.chunks]

        parsed = _safe_json_loads(
            self._structured(system, user, max_tokens=4096, temperature=0.2),
            label="Cerebras tasks extraction",
        )
        items = parsed.get("tasks", []) if isinstance(parsed, dict) else []

        out: list[ExtractedTask] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            idxs = item.get("chunkIndexes") or []
            ids = [
                chunk_ids[i - 1]
                for i in idxs
                if isinstance(i, int) and 1 <= i <= len(chunk_ids)
            ]
            if not ids and chunk_ids:
                ids = [chunk_ids[0]]
            linked = item.get("linkedRequirementTitle")
            out.append(ExtractedTask(
                title=title,
                description=str(item.get("description", "")).strip(),
                chunkIds=ids,
                linkedRequirementTitle=str(linked) if linked else None,
            ))
        return out

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        system_prompt, user_prompt = build_coverage_prompt(input)
        parsed = _safe_json_loads(
            self._structured(system_prompt, user_prompt, max_tokens=1024, temperature=0.2),
            label="Cerebras coverage audit",
        )
        judgments = [
            CoverageJudgment(
                status=_normalize_status(j.get("status")),
                rationale=j.get("rationale", ""),
            )
            for j in parsed.get("judgments", [])
        ] if isinstance(parsed, dict) else []
        return AIAuditCoverageOutput(judgments=judgments)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        answer = self._post_with_retry({
            "model": self._model,
            "messages": [
                {"role": "system", "content": "You are a project risk analyst. Be concise."},
                {"role": "user", "content": build_risk_summary_prompt(input)},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        })
        return AIRiskSummaryOutput(summary=answer)


# ---- Gemini provider ----

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAIProvider:
    """Gemini (Google) — REST generateContent.

    Primary provider for structured extraction/audit under ``LLM_PROVIDER=routing``.
    JSON-mode responses (``responseMimeType: "application/json"``) are parsed with
    ``_safe_json_loads``; failures raise so the fallback chain (Groq → stub) can
    engage. Also serves as chat fallback.
    """

    id = "gemini"
    parallel_audit = True

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._api_key = api_key

    def _generate(self, body: dict[str, object]) -> str:
        url = f"{GEMINI_BASE}/{self._model}:generateContent?key={self._api_key}"
        resp = httpx.post(url, json=body, timeout=90)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini LLM failed: {resp.status_code} {resp.text}")

        candidates = resp.json().get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    def _generate_with_retry(self, body: dict[str, object], *, attempts: int = 3) -> str:
        """generateContent with bounded retry on rate limits (429) and transient errors."""
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return self._generate(body)
            except Exception as exc:
                if not _is_retryable(exc) or attempt == attempts - 1:
                    raise
                wait = _parse_retry_after(str(exc))
                logger.warning(
                    "Gemini rate limited (attempt %d/%d) — retrying in %.1fs",
                    attempt + 1,
                    attempts,
                    wait,
                )
                time.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"Gemini LLM failed after {attempts} attempts: {last_exc}")

    def _structured(
        self, system: str, user: str, *, max_tokens: int, temperature: float
    ) -> str:
        return self._generate_with_retry({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {"thinkingLevel": "minimal"},
            },
        })

    def chat(self, input: AIChatInput) -> AIChatOutput:
        contents: list[dict[str, object]] = []
        for m in input.history:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        contents.append({"role": "user", "parts": [{"text": input.question}]})

        answer = self._generate_with_retry({
            "systemInstruction": {"parts": [{"text": _build_system_prompt(input)}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.3},
        })
        return AIChatOutput(answer=answer, citations=_build_citations(input.passages))

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        system, user = build_extract_requirements_prompt(input)
        chunk_ids = [str(c.get("id", "")) for c in input.chunks]

        parsed = _safe_json_loads(
            self._structured(system, user, max_tokens=8192, temperature=0.2),
            label="Gemini requirements extraction",
        )
        items = parsed.get("requirements", []) if isinstance(parsed, dict) else []

        out: list[ExtractedRequirement] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            idxs = item.get("chunkIndexes") or []
            ids = [
                chunk_ids[i - 1]
                for i in idxs
                if isinstance(i, int) and 1 <= i <= len(chunk_ids)
            ]
            if not ids and chunk_ids:
                ids = [chunk_ids[0]]
            out.append(ExtractedRequirement(
                title=title,
                description=str(item.get("description", "")).strip(),
                chunkIds=ids,
            ))
        return out

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        system, user = build_extract_tasks_prompt(input)
        chunk_ids = [str(c.get("id", "")) for c in input.chunks]

        parsed = _safe_json_loads(
            self._structured(system, user, max_tokens=8192, temperature=0.2),
            label="Gemini tasks extraction",
        )
        items = parsed.get("tasks", []) if isinstance(parsed, dict) else []

        out: list[ExtractedTask] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            idxs = item.get("chunkIndexes") or []
            ids = [
                chunk_ids[i - 1]
                for i in idxs
                if isinstance(i, int) and 1 <= i <= len(chunk_ids)
            ]
            if not ids and chunk_ids:
                ids = [chunk_ids[0]]
            linked = item.get("linkedRequirementTitle")
            out.append(ExtractedTask(
                title=title,
                description=str(item.get("description", "")).strip(),
                chunkIds=ids,
                linkedRequirementTitle=str(linked) if linked else None,
            ))
        return out

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        system_prompt, user_prompt = build_coverage_prompt(input)

        parsed = _safe_json_loads(
            self._structured(system_prompt, user_prompt, max_tokens=1024, temperature=0.2),
            label="Gemini coverage audit",
        )
        judgments = [
            CoverageJudgment(
                status=_normalize_status(j.get("status")),
                rationale=j.get("rationale", ""),
            )
            for j in parsed.get("judgments", [])
        ] if isinstance(parsed, dict) else []
        return AIAuditCoverageOutput(judgments=judgments)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        answer = self._generate_with_retry({
            "systemInstruction": {"parts": [{"text": "You are a project risk analyst. Be concise."}]},
            "contents": [{"role": "user", "parts": [{"text": build_risk_summary_prompt(input)}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
        })
        return AIRiskSummaryOutput(summary=answer)


# ---- Fallback provider ----

class FallbackAIProvider:
    """Try the primary provider, then backups, on retryable failures.

    Used under ``LLM_PROVIDER=routing`` so Gemini can serve the structured roles
    (extraction/audit) with Groq and finally the heuristic stub as fallbacks.
    ``None`` slots are skipped, so an unconfigured primary (e.g. missing Gemini
    keys) degrades cleanly to the next provider.
    """

    id = "fallback"

    def __init__(self, primary: AIProvider | None, *backups: AIProvider | None) -> None:
        self._chain = [p for p in (primary, *backups) if p is not None]
        self.parallel_audit = bool(self._chain) and self._chain[0].id in ("gemini",)

    def _call(self, method: str, *args: object, **kwargs: object):
        if not self._chain:
            raise RuntimeError("FallbackAIProvider has no providers configured")
        for i, provider in enumerate(self._chain):
            try:
                return getattr(provider, method)(*args, **kwargs)
            except Exception as exc:
                if not _is_retryable(exc) or i == len(self._chain) - 1:
                    raise
                logger.warning(
                    "Provider %s failed (%s) — falling back to %s",
                    provider.id,
                    exc,
                    self._chain[i + 1].id,
                )
        raise RuntimeError("FallbackAIProvider exhausted all providers")

    def chat(self, input: AIChatInput) -> AIChatOutput:
        return self._call("chat", input)

    def _structured(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str:
        return self._call(
            "_structured", system, user, max_tokens=max_tokens, temperature=temperature
        )

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        return self._call("extract_requirements", input)

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        return self._call("extract_tasks", input)

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        return self._call("audit_coverage", input)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        return self._call("risk_summary", input)


# ---- Routing provider ----


class RoutingAIProvider:
    """Per-task routing: chat → Groq, extraction → Gemini, audit → Gemini.

    Each role is a ``FallbackAIProvider`` chain so a role degrades to the next
    configured provider on retryable failure.
    """

    id = "routing"

    def __init__(
        self,
        chat: AIProvider,
        extract: AIProvider,
        audit: AIProvider,
    ) -> None:
        self._chat = chat
        self._extract = extract
        self._audit = audit
        self.parallel_audit = getattr(audit, "parallel_audit", False)

    def chat(self, input: AIChatInput) -> AIChatOutput:
        return self._chat.chat(input)

    def _structured(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str:
        """Delegate structured (JSON-mode) generation to the extraction chain.

        Enables the decomposed PR verification pipeline (Stage 2/3) and
        requirement extraction to use the LLM under ``LLM_PROVIDER=routing``
        instead of silently degrading to the keyword heuristic.
        """
        return self._extract._structured(
            system, user, max_tokens=max_tokens, temperature=temperature
        )

    def extract_requirements(self, input: AIExtractRequirementsInput) -> list[ExtractedRequirement]:
        return self._extract.extract_requirements(input)

    def extract_tasks(self, input: AIExtractTasksInput) -> list[ExtractedTask]:
        return self._extract.extract_tasks(input)

    def audit_coverage(self, input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
        return self._audit.audit_coverage(input)

    def risk_summary(self, input: AIRiskSummaryInput) -> AIRiskSummaryOutput:
        return self._audit.risk_summary(input)


# ---- Factory ----


def _build_cerebras(settings) -> CerebrasAIProvider | None:
    if not settings.cerebras_api_key:
        return None
    return CerebrasAIProvider(settings.cerebras_api_key, settings.cerebras_model)


def _build_groq(settings, model: str) -> GroqAIProvider | None:
    if not settings.groq_api_key:
        logger.warning("LLM_PROVIDER=routing: GROQ_API_KEY missing — using stub for Groq roles.")
        return None
    return GroqAIProvider(settings.groq_api_key, model)


def _build_gemini(settings, model: str) -> GeminiAIProvider | None:
    if not settings.gemini_api_key:
        logger.warning("LLM_PROVIDER=routing: GEMINI_API_KEY missing — using stub for Gemini roles.")
        return None
    return GeminiAIProvider(settings.gemini_api_key, model)


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "routing":
        stub = StubAIProvider()
        cerebras = _build_cerebras(settings)
        gemini = _build_gemini(settings, settings.gemini_chat_model)
        gemini_audit = _build_gemini(settings, settings.gemini_audit_model)
        groq_chat = _build_groq(settings, settings.groq_chat_model)
        groq_extract = _build_groq(settings, settings.groq_extract_model)
        groq_audit = _build_groq(settings, settings.groq_audit_model)

        return RoutingAIProvider(
            chat=FallbackAIProvider(
                cerebras,
                groq_chat,
                gemini,
                stub,
            ),
            extract=FallbackAIProvider(
                cerebras,
                gemini,
                groq_extract,
                stub,
            ),
            audit=FallbackAIProvider(
                cerebras,
                gemini_audit,
                groq_audit,
                stub,
            ),
        )

    if provider == "cerebras":
        cerebras = _build_cerebras(settings)
        if not cerebras:
            logger.warning("LLM_PROVIDER=cerebras but CEREBRAS_API_KEY missing. Using stub.")
            return StubAIProvider()
        return cerebras

    if provider == "groq":
        if not settings.groq_api_key:
            logger.warning("LLM_PROVIDER=groq but GROQ_API_KEY missing. Using stub.")
            return StubAIProvider()
        return GroqAIProvider(settings.groq_api_key, settings.groq_audit_model)

    if provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning("LLM_PROVIDER=gemini but GEMINI_API_KEY missing. Using stub.")
            return StubAIProvider()
        return GeminiAIProvider(settings.gemini_api_key, settings.gemini_chat_model)

    if provider == "fireworks":
        if not settings.fireworks_api_key:
            logger.warning("LLM_PROVIDER=fireworks but FIREWORKS_API_KEY missing. Using stub.")
            return StubAIProvider()
        return FireworksAIProvider(settings.fireworks_api_key, settings.fireworks_model)

    return StubAIProvider()
