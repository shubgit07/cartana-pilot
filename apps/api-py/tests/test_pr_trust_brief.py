"""End-to-End integration tests for POST /projects/{project_id}/audit/verify-pr.

Verifies:
1. Submitting git diff + spec markdown generates PRTrustBrief with fromCache: false.
2. Immediate re-submitting identical payload hits Upstash/Memory cache with fromCache: true (0 LLM cost).
3. Validation errors on empty diff input.
4. When the LLM cannot produce structured verdicts, the endpoint fails loudly
   (502) instead of degrading to keyword heuristics.
"""
from __future__ import annotations

import json

import pytest

from tests.conftest import seed_project

SAMPLE_SPEC = """# Authentication Specs
- R1: Must support email and password user login API
- R2: Must sanitize input and validate email format
"""

SAMPLE_DIFF = """diff --git a/apps/api-py/app/api/routes/auth.py b/apps/api-py/app/api/routes/auth.py
new file mode 100644
index 0000000..abcdef1
--- /dev/null
+++ b/apps/api-py/app/api/routes/auth.py
@@ -0,0 +1,8 @@
+from fastapi import APIRouter
+
+router = APIRouter()
+
+@router.post("/login")
+def login(email: str, password: str):
+    # Sanitizes input and validates email format
+    return {"status": "ok"}
"""


class FakeStructuredProvider:
    """Deterministic LLM provider used to exercise the verify-pr pipeline."""

    id = "fake-structured"

    def _structured(self, system: str, user: str, *, max_tokens: int, temperature: float) -> str:
        if "SPECIFICATION DOCUMENT TEXT" in user:
            return json.dumps({
                "requirements": [
                    {"id": "R1", "title": "User login API", "description": "Support email and password login", "kind": "functional"},
                    {"id": "R2", "title": "Input sanitization", "description": "Sanitize input and validate email format", "kind": "functional"},
                ]
            })
        if "Git Diff Hunks" in user:
            return json.dumps({
                "verdicts": [
                    {"reqId": "R1", "title": "User login API", "status": "covered", "confidence": "high",
                     "evidenceFile": "apps/api-py/app/api/routes/auth.py", "evidenceSnippet": "@router.post(\"/login\")", "rationale": "Login endpoint present."},
                    {"reqId": "R2", "title": "Input sanitization", "status": "covered", "confidence": "high",
                     "evidenceFile": "apps/api-py/app/api/routes/auth.py", "evidenceSnippet": "# Sanitizes input", "rationale": "Sanitization comment present."},
                ]
            })
        if "Verification Verdicts" in user:
            return json.dumps({
                "coverageScore": 100,
                "trustLevel": "high",
                "summary": "PR covers all requirements.",
                "riskAlerts": [],
            })
        raise AssertionError(f"Unexpected structured prompt: {user[:80]}")


@pytest.fixture()
def fake_llm_provider(monkeypatch):
    fake = FakeStructuredProvider()
    monkeypatch.setattr("app.api.services.input_service.get_ai_provider", lambda: fake)
    monkeypatch.setattr("app.api.services.audit_service.get_ai_provider", lambda: fake)
    return fake


def test_verify_pr_initial_run_and_cache_hit(client, db_session, fake_llm_provider):
    project = seed_project(db_session)

    payload = {
        "specText": SAMPLE_SPEC,
        "rawDiff": SAMPLE_DIFF,
    }

    # 1. Initial Verification Run
    resp = client.post(f"/projects/{project.id}/audit/verify-pr", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert "brief" in data
    assert data["fromCache"] is False

    brief = data["brief"]
    assert brief["projectId"] == project.id
    assert brief["totalRequirements"] >= 1
    assert brief["coverageScore"] >= 0
    assert brief["trustLevel"] in ("high", "medium", "low")
    assert len(brief["verdicts"]) >= 1
    assert len(brief["changedFilesSummary"]) == 1
    assert brief["changedFilesSummary"][0]["filename"] == "apps/api-py/app/api/routes/auth.py"

    # 2. Immediate Re-run (Deduplication Cache Hit)
    resp_cached = client.post(f"/projects/{project.id}/audit/verify-pr", json=payload)
    assert resp_cached.status_code == 200

    data_cached = resp_cached.json()
    assert data_cached["fromCache"] is True
    assert data_cached["brief"]["id"] == brief["id"]


def test_verify_pr_missing_diff_error(client, db_session):
    project = seed_project(db_session)

    # Empty payload (no rawDiff or githubPrUrl)
    resp = client.post(f"/projects/{project.id}/audit/verify-pr", json={})
    assert resp.status_code == 400
    assert "No git diff provided" in resp.json()["error"]["message"]


def test_verify_pr_fails_loudly_without_llm(client, db_session, monkeypatch):
    """No provider (no _structured, no usable chat) -> 502, never heuristics."""
    project = seed_project(db_session)

    class NoLLMProvider:
        id = "broken"

        def chat(self, input):
            return type("Out", (), {"answer": "no structured output"})()

    from app.api.services import audit_service, input_service

    monkeypatch.setattr(audit_service, "get_ai_provider", lambda: NoLLMProvider())
    monkeypatch.setattr(input_service, "get_ai_provider", lambda: NoLLMProvider())

    resp = client.post(
        f"/projects/{project.id}/audit/verify-pr",
        json={
            "specText": f"{SAMPLE_SPEC}\n# variant: no-llm",
            "rawDiff": SAMPLE_DIFF,
        },
    )

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "llm_service_error"


def test_verify_pr_does_not_use_heuristics_on_unparseable_json(client, db_session, monkeypatch):
    """Even a non-JSON structured response must not degrade to heuristics."""
    project = seed_project(db_session)

    class GarbageProvider:
        id = "garbage"

        def _structured(self, system, user, *, max_tokens, temperature):
            return "this is not json"

        def chat(self, input):
            return type("Out", (), {"answer": "also not json"})()

    from app.api.services import audit_service, input_service

    monkeypatch.setattr(audit_service, "get_ai_provider", lambda: GarbageProvider())
    monkeypatch.setattr(input_service, "get_ai_provider", lambda: GarbageProvider())

    resp = client.post(
        f"/projects/{project.id}/audit/verify-pr",
        json={
            "specText": f"{SAMPLE_SPEC}\n# variant: unparseable",
            "rawDiff": SAMPLE_DIFF,
        },
    )

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "llm_service_error"
