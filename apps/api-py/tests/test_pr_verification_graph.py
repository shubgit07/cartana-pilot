"""Unit & Integration Tests for Stateful LangGraph PR Verification Workflow."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.api.schemas.audit import (
    PRRiskAlert,
    PRTrustBrief,
    RequirementVerificationVerdict,
)
from app.core.errors import ValidationError
from app.core.workflow.pr_verification_graph import (
    PRVerificationState,
    build_pr_verification_graph,
    check_cache_node,
    clean_diff_node,
    extract_spec_node,
    run_pr_verification_workflow,
)

SAMPLE_SPEC = """
# Feature Brief
## Requirements
- R1: User registration and login with JWT.
- R2: Task CRUD endpoints for authenticated users.
"""

SAMPLE_DIFF = """
diff --git a/app/routes/auth.py b/app/routes/auth.py
new file mode 100644
--- /dev/null
+++ b/app/routes/auth.py
@@ -0,0 +1,15 @@
+@router.post("/login")
+def login(email: str, password: str):
+    return {"token": "jwt-xyz"}
+
diff --git a/package-lock.json b/package-lock.json
new file mode 100644
--- /dev/null
+++ b/package-lock.json
@@ -0,0 +1,500 @@
+{"name": "lockfile-noise", "version": "1.0.0"}
+"""


def test_build_pr_verification_graph():
    """Verify that the LangGraph StateGraph compiles successfully."""
    graph = build_pr_verification_graph()
    assert graph is not None


def test_langgraph_clean_diff_node_strips_noise():
    """Verify that the clean_diff node filters noise like package-lock.json."""
    state: PRVerificationState = {
        "raw_diff": SAMPLE_DIFF,
    }
    result = clean_diff_node(state)
    assert "changed_files" in result
    assert "compressed_diff" in result

    # Should only keep auth.py, package-lock.json is stripped
    filenames = [f["filename"] for f in result["changed_files"]]
    assert "app/routes/auth.py" in filenames
    assert "package-lock.json" not in filenames


def test_langgraph_missing_diff_raises_validation_error():
    """Verify that an empty diff raises a ValidationError in clean_diff_node."""
    state: PRVerificationState = {"raw_diff": ""}
    with pytest.raises(ValidationError, match="No git diff provided"):
        clean_diff_node(state)


def test_langgraph_missing_spec_raises_validation_error():
    """Verify that empty spec and requirements raise a ValidationError."""
    state: PRVerificationState = {"spec_text": "", "requirements": []}
    with pytest.raises(ValidationError, match="No requirements found"):
        extract_spec_node(state)


@patch("app.core.workflow.pr_verification_graph.get_cached_audit")
def test_langgraph_cache_hit_returns_early(mock_get_cache):
    """Verify that check_cache_node flags cache_hit=True when key exists in Redis."""
    cached_brief_data = {
        "id": "run-test123",
        "projectId": "proj-1",
        "title": "PR Trust Brief (HIGH Trust)",
        "coverageScore": 95,
        "trustLevel": "high",
        "summary": "Cached audit summary",
        "totalRequirements": 2,
        "coveredCount": 2,
        "partialCount": 0,
        "missingCount": 0,
        "verdicts": [],
        "riskAlerts": [],
        "changedFilesSummary": [],
        "createdAt": "2026-08-28T00:00:00Z",
    }
    mock_get_cache.return_value = cached_brief_data

    state: PRVerificationState = {
        "spec_text": "sample spec",
        "raw_diff": "sample diff",
    }

    result = check_cache_node(state)
    assert result["cache_hit"] is True
    assert isinstance(result["final_brief"], PRTrustBrief)
    assert result["final_brief"].coverageScore == 95


@patch("app.core.workflow.pr_verification_graph.get_cached_audit", return_value=None)
@patch("app.core.workflow.pr_verification_graph.cache_audit")
def test_run_pr_verification_workflow_e2e(mock_cache_audit, mock_get_cached):
    """Verify full end-to-end execution of the LangGraph workflow."""
    fake_verdicts = [
        RequirementVerificationVerdict(
            reqId="R1",
            title="User registration",
            status="covered",
            confidence="high",
            evidenceFile="app/routes/auth.py",
            evidenceSnippet="+ @router.post('/login')",
            rationale="Auth route implemented.",
        )
    ]
    fake_alerts = [
        PRRiskAlert(
            kind="no_tests",
            severity="info",
            title="No tests in PR",
            description="Add test coverage.",
            affectedFiles=["app/routes/auth.py"],
        )
    ]

    with patch("app.core.workflow.pr_verification_graph._run_stage2_verification", return_value=fake_verdicts), \
         patch("app.core.workflow.pr_verification_graph._run_stage3_risk_analysis", return_value=(90, "high", "High trust summary", fake_alerts)):

        brief, is_cached = run_pr_verification_workflow(
            project_id="proj-test",
            user_id="dev-user",
            spec_text=SAMPLE_SPEC,
            raw_diff=SAMPLE_DIFF,
            requirements=[{"id": "R1", "title": "User registration", "description": "JWT auth", "kind": "functional"}],
            db=None,
        )

        assert is_cached is False
        assert brief is not None
        assert brief.coverageScore == 90
        assert brief.trustLevel == "high"
        assert len(brief.verdicts) == 1
        assert brief.verdicts[0].status == "covered"
        assert len(brief.riskAlerts) == 1
        assert mock_cache_audit.called


def test_code_verifier_node_injects_repo_context(db_session):
    """Hybrid retrieval: indexed baseline code reaches the Stage 2 prompt."""
    import json

    from app.api.services.repo_index_service import IndexFileInput, sync_repository_snapshot
    from app.core.workflow.pr_verification_graph import code_verifier_node
    from tests.conftest import seed_project

    project = seed_project(db_session)
    sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[
            IndexFileInput(
                path="middleware/auth.py",
                content="def require_auth(request):\n    if not request.user:\n        raise Forbidden()\n",
            )
        ],
    )

    captured: dict[str, str] = {}

    class FakeProvider:
        def _structured(self, system_prompt, user_prompt, **kwargs):
            captured["user_prompt"] = user_prompt
            return json.dumps({
                "verdicts": [{
                    "reqId": "R1",
                    "title": "Auth guard",
                    "status": "covered",
                    "confidence": "high",
                    "evidenceFile": "middleware/auth.py",
                    "evidenceSnippet": "def require_auth(request):",
                    "rationale": "Guard exists in repository context.",
                }]
            })

    with patch(
        "app.core.workflow.pr_verification_graph.get_ai_provider", return_value=FakeProvider()
    ):
        result = code_verifier_node({
            "project_id": project.id,
            "requirements": [{"id": "R1", "title": "Only authenticated users act",
                              "description": "require auth guard"}],
            "changed_files": [],
            "compressed_diff": "FILE: other.py [modified]\n  Hunk: @@ -1 +1 @@\n  + x = 1",
            "db": db_session,
        })

    assert result["verdicts"][0].status == "covered"
    assert result["repo_context"] != ""
    assert "middleware/auth.py" in captured["user_prompt"]
    assert "Repository Context" in captured["user_prompt"]


def test_code_verifier_node_degrades_to_diff_only_without_db():
    """No DB session (or empty index) must not break verification."""
    import json

    from app.core.workflow.pr_verification_graph import code_verifier_node

    class FakeProvider:
        def _structured(self, system_prompt, user_prompt, **kwargs):
            assert "Repository Context" not in user_prompt
            return json.dumps({
                "verdicts": [{
                    "reqId": "R1",
                    "title": "T",
                    "status": "missing",
                    "confidence": "high",
                    "evidenceFile": None,
                    "evidenceSnippet": None,
                    "rationale": "Absent from diff.",
                }]
            })

    with patch(
        "app.core.workflow.pr_verification_graph.get_ai_provider", return_value=FakeProvider()
    ):
        result = code_verifier_node({
            "project_id": "proj-x",
            "requirements": [{"id": "R1", "title": "T", "description": "D"}],
            "changed_files": [],
            "compressed_diff": "FILE: a.py [modified]\n  Hunk: @@ -1 +1 @@\n  + x = 1",
            "db": None,
        })

    assert result["repo_context"] == ""
    assert result["verdicts"][0].status == "missing"
