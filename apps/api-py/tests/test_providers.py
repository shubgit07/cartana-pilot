"""Tests for the AI provider layer.

Covers Gemini structured parsing, the retryable-error classifier, and the
fallback chain wiring (primary → backup). HTTP calls are mocked; no network
access or API keys are required.
"""
from __future__ import annotations

import httpx
import pytest

from app.providers.ai_provider import (
    AIExtractRequirementsInput,
    ExtractedRequirement,
    FallbackAIProvider,
    GeminiAIProvider,
    _is_retryable,
    _parse_retry_after,
    _safe_json_loads,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)
        self.headers: dict[str, str] = {}

    def json(self) -> dict:
        return self._payload

    def __str__(self) -> str:
        return f"status={self.status_code} {self._payload}"


def _patch_post(monkeypatch, responses: list[_FakeResponse]):
    calls: list[dict] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json or {})
        return responses.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


def _reqs_input():
    return AIExtractRequirementsInput(
        sourceFilename="spec.pdf",
        chunks=[
            {"id": "c1", "position": 0, "text": "The app must support SSO login."},
            {"id": "c2", "position": 1, "text": "Users can export reports as PDF."},
        ],
    )


def _gemini_response(content: str) -> _FakeResponse:
    return _FakeResponse(
        200,
        {"candidates": [{"content": {"parts": [{"text": content}]}}]},
    )


def _make_gemini() -> GeminiAIProvider:
    return GeminiAIProvider(api_key="gk", model="gemini-3.6-flash")


def test_safe_json_loads_strips_markdown_fences():
    parsed = _safe_json_loads('```json\n{"requirements": []}\n```', label="test")
    assert parsed == {"requirements": []}


def test_safe_json_loads_isolates_outer_object():
    parsed = _safe_json_loads('Here is the result: {"a": 1} thanks!', label="test")
    assert parsed == {"a": 1}


def test_safe_json_loads_passes_through_parsed_dict():
    parsed = _safe_json_loads({"requirements": [{"title": "X"}]}, label="test")
    assert parsed == {"requirements": [{"title": "X"}]}


def test_safe_json_loads_raises_without_matching_brace():
    with pytest.raises(RuntimeError, match="invalid JSON"):
        _safe_json_loads("definitely not json", label="test")


# ---- Gemini structured parsing ----


def test_gemini_extract_requirements_parses_json(monkeypatch):
    provider = _make_gemini()
    _patch_post(monkeypatch, [
        _gemini_response(
            '{"requirements": ['
            '{"title": "Support SSO login", "description": "The app must support SSO login.", "chunkIndexes": [1]},'
            '{"title": "Export reports as PDF", "description": "Users can export reports.", "chunkIndexes": [2]}'
            "]}"
        ),
    ])

    out = provider.extract_requirements(_reqs_input())

    assert len(out) == 2
    assert out[0] == ExtractedRequirement(
        title="Support SSO login",
        description="The app must support SSO login.",
        chunkIds=["c1"],
    )
    assert out[1].chunkIds == ["c2"]


def test_gemini_extract_requirements_raises_on_invalid_json(monkeypatch):
    provider = _make_gemini()
    _patch_post(monkeypatch, [_gemini_response("not json at all")])

    with pytest.raises(RuntimeError, match="invalid JSON"):
        provider.extract_requirements(_reqs_input())


'''Removed standalone task/coverage tests.

The requirement-to-task coverage path (extract_tasks / audit_coverage /
risk_summary and their AI types) was eliminated from the product: Cartana
verifies PRs against requirements directly. These tests are kept as a
tombstone so the removal stays visible in history.


def test_gemini_extract_tasks_parses_linked_requirement(monkeypatch):
    provider = _make_gemini()
    _patch_post(monkeypatch, [
        _gemini_response(
            '{"tasks": [{"title": "Build login flow", "description": "Implement SSO.", '
            '"chunkIndexes": [1], "linkedRequirementTitle": "Support SSO login"}]}'
        ),
    ])

    out = provider.extract_tasks(AIExtractTasksInput(
        sourceFilename="spec.pdf",
        chunks=[{"id": "c1", "position": 0, "text": "The app must support SSO login."}],
        requirements=[{"title": "Support SSO login"}],
    ))

    assert len(out) == 1
    assert out[0] == ExtractedTask(
        title="Build login flow",
        description="Implement SSO.",
        chunkIds=["c1"],
        linkedRequirementTitle="Support SSO login",
    )


def test_gemini_audit_coverage_parses_and_normalizes_status(monkeypatch):
    provider = _make_gemini()
    _patch_post(monkeypatch, [
        _gemini_response(
            '{"judgments": ['
            '{"status": "covered", "rationale": "fully"},'
            '{"status": "bogus", "rationale": "unknown"}'
            "]}"
        ),
    ])

    out = provider.audit_coverage(AIAuditCoverageInput(
        requirement={"title": "Support SSO login", "description": ""},
        candidateTasks=[{"title": "Build login flow"}, {"title": "Export PDFs"}],
    ))

    assert isinstance(out, AIAuditCoverageOutput)
    assert [j.status for j in out.judgments] == ["covered", "unclear"]


def test_gemini_risk_summary_returns_text(monkeypatch):
    provider = _make_gemini()
    _patch_post(monkeypatch, [_gemini_response("2/3 requirements covered.")])

    out = provider.risk_summary(AIRiskSummaryInput(
        requirements=[
            {"title": "A", "status": "covered"},
            {"title": "B", "status": "missing"},
        ],
        findings=[{"severity": "high"}],
    ))

    assert out.summary == "2/3 requirements covered."
'''


# ---- Retryable classification ----


def test_is_retryable_classifies_errors():
    assert _is_retryable(RuntimeError("Groq LLM failed: 429 rate limited"))
    assert _is_retryable(RuntimeError("Provider LLM failed: 403 ... 5035 ..."))
    assert _is_retryable(RuntimeError("Provider LLM failed: 500 Internal Server Error"))
    assert _is_retryable(RuntimeError("Provider returned invalid JSON for requirements"))
    assert _is_retryable(httpx.TimeoutException("timed out"))
    assert not _is_retryable(RuntimeError("Provider LLM failed: 400 bad request"))


def test_parse_retry_after():
    assert _parse_retry_after("Try again in 3.5s.") == 3.5
    assert _parse_retry_after("no delay present") == 15.0


def test_gemini_retries_429_then_succeeds(monkeypatch):
    provider = _make_gemini()
    responses = [
        _FakeResponse(429, {"error": {"message": "Too fast."}}, text="Too fast. Try again in 0.1s."),
        _gemini_response("retried ok"),
    ]
    calls = _patch_post(monkeypatch, responses)

    assert provider._generate_with_retry({"contents": []}, attempts=3) == "retried ok"
    assert len(calls) == 2


# ---- Fallback chain (live requirement-extraction role) ----


class _FakeExtractProvider:
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls = 0
        self.id = "fake"

    def extract_requirements(self, input: AIExtractRequirementsInput):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_fallback_uses_backup_on_retryable_failure():
    result = [ExtractedRequirement(title="R", description="", chunkIds=[])]
    primary = _FakeExtractProvider(RuntimeError("429 rate limited"))
    backup = _FakeExtractProvider(result)

    fallback = FallbackAIProvider(primary, backup)

    assert fallback.extract_requirements(_reqs_input()) is result
    assert primary.calls == 1
    assert backup.calls == 1


def test_fallback_reraises_non_retryable():
    primary = _FakeExtractProvider(RuntimeError("400 bad request"))
    backup = _FakeExtractProvider([])

    fallback = FallbackAIProvider(primary, backup)

    with pytest.raises(RuntimeError, match="400"):
        fallback.extract_requirements(_reqs_input())
    assert backup.calls == 0


def test_fallback_skips_none_slots():
    result = [ExtractedRequirement(title="R", description="", chunkIds=[])]
    backup = _FakeExtractProvider(result)

    fallback = FallbackAIProvider(None, backup)

    assert fallback.extract_requirements(_reqs_input()) is result
    assert fallback.parallel_audit is False
