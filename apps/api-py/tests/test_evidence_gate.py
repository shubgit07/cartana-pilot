"""Deterministic evidence gate: validation, scoring, trust, cache scoping."""
from __future__ import annotations

from unittest.mock import patch

from app.api.schemas.audit import PRRiskAlert, RequirementVerificationVerdict
from app.core.evidence import (
    build_diff_index,
    compute_coverage_score,
    compute_trust_level,
    normalize_path,
    snippet_found_in,
    validate_evidence,
)
from app.core.workflow.pr_verification_graph import (
    PRVerificationState,
    clean_diff_node,
    verify_evidence_node,
)
from tests.test_pr_verification_graph import SAMPLE_DIFF


def _verdict(**overrides) -> RequirementVerificationVerdict:
    base: dict = {
        "reqId": "R1",
        "title": "Login API",
        "status": "covered",
        "confidence": "high",
        "evidenceFile": "app/routes/auth.py",
        "evidenceSnippet": '@router.post("/login")',
        "rationale": "Login endpoint present.",
    }
    base.update(overrides)
    return RequirementVerificationVerdict(**base)


def _diff_index() -> dict[str, str]:
    result = clean_diff_node({"raw_diff": SAMPLE_DIFF})
    return result["diff_index"]


def test_normalize_path_strips_prefixes_and_case():
    assert normalize_path("a/src/App.tsx") == "src/app.tsx"
    assert normalize_path("./src/App.tsx") == "src/app.tsx"
    assert normalize_path("src\\App.tsx") == "src/app.tsx"


def test_build_diff_index_maps_old_and_new_paths():
    index = _diff_index()
    assert "app/routes/auth.py" in index
    assert index["app/routes/auth.py"] != ""


def test_verbatim_evidence_is_verified():
    verdicts, verified, unverified = validate_evidence([_verdict()], _diff_index())
    assert verified == 1
    assert unverified == 0
    assert verdicts[0].evidenceVerified is True
    assert verdicts[0].status == "covered"


def test_marker_prefixed_snippet_is_verified():
    verdict = _verdict(evidenceSnippet="+def login(email: str, password: str):")
    verdicts, verified, _unverified = validate_evidence([verdict], _diff_index())
    assert verified == 1
    assert verdicts[0].evidenceVerified is True


def test_multiline_block_match():
    verdict = _verdict(
        evidenceSnippet='@router.post("/login")\ndef login(email: str, password: str):'
    )
    verdicts, verified, _unverified = validate_evidence([verdict], _diff_index())
    assert verified == 1
    assert verdicts[0].evidenceVerified is True


def test_hallucinated_file_is_downgraded():
    verdict = _verdict(evidenceFile="src/invented.tsx", evidenceSnippet="const x = 1;")
    verdicts, verified, unverified = validate_evidence([verdict], _diff_index())
    assert verified == 0
    assert unverified == 1
    assert verdicts[0].evidenceVerified is False
    assert verdicts[0].status == "unclear"
    assert verdicts[0].confidence == "low"
    assert verdicts[0].rationale.startswith("evidence not found in the diff:")


def test_hallucinated_snippet_in_real_file_is_downgraded():
    verdict = _verdict(evidenceSnippet="def totally_made_up_function():")
    verdicts, verified, unverified = validate_evidence([verdict], _diff_index())
    assert verified == 0
    assert unverified == 1
    assert verdicts[0].status == "unclear"


def test_unverified_partial_is_downgraded():
    verdict = _verdict(status="partial", evidenceSnippet="def invented(): pass")
    verdicts, _verified, unverified = validate_evidence([verdict], _diff_index())
    assert unverified == 1
    assert verdicts[0].status == "unclear"


def test_missing_verdict_without_evidence_is_left_alone():
    verdict = _verdict(status="missing", evidenceFile=None, evidenceSnippet=None)
    verdicts, verified, unverified = validate_evidence([verdict], _diff_index())
    assert verified == 0
    assert unverified == 0
    assert verdicts[0].evidenceVerified is None
    assert verdicts[0].status == "missing"


def test_repo_context_evidence_is_accepted():
    verdict = _verdict(
        evidenceFile="middleware/auth.py",
        evidenceSnippet="def require_auth(request):",
    )
    repo_context = "FILE: middleware/auth.py\n  + def require_auth(request):\n  +     raise Forbidden()"
    verdicts, verified, _unverified = validate_evidence([verdict], {}, repo_context)
    assert verified == 1
    assert verdicts[0].evidenceVerified is True


def test_snippet_found_in_block_and_line_wise():
    corpus = "x = 1\ndef login(email):\n    return token"
    assert snippet_found_in("def login(email):", corpus)
    assert snippet_found_in("x = 1\ndef login(email):", corpus)
    assert not snippet_found_in("def logout(email):", corpus)


def test_compute_coverage_score_math():
    assert compute_coverage_score([]) == 0
    covered = _verdict()
    partial = _verdict(status="partial")
    missing = _verdict(status="missing", evidenceFile=None, evidenceSnippet=None)
    assert compute_coverage_score([covered]) == 100
    assert compute_coverage_score([partial]) == 50
    assert compute_coverage_score([covered, partial, missing]) == 50


def test_compute_trust_level_thresholds():
    covered = _verdict()
    unverified = _verdict(status="unclear", evidenceVerified=False)
    missing = _verdict(status="missing", evidenceFile=None, evidenceSnippet=None)
    critical = PRRiskAlert(
        kind="security_gap", severity="critical", title="t", description="d"
    )

    assert compute_trust_level([covered], [], 100) == "high"
    assert compute_trust_level([covered], [], 60) == "medium"
    assert compute_trust_level([covered], [critical], 90) == "low"
    assert compute_trust_level([covered], [], 40) == "low"
    assert compute_trust_level([covered, unverified], [], 75) == "medium"
    assert compute_trust_level([covered, missing], [], 50) == "medium"


def test_verify_evidence_node_counts():
    state: PRVerificationState = {
        "verdicts": [
            _verdict(),
            _verdict(reqId="R2", evidenceFile="src/invented.tsx"),
        ],
        "diff_index": _diff_index(),
        "repo_context": "",
    }
    result = verify_evidence_node(state)
    assert result["evidence_verified_count"] == 1
    assert result["evidence_unverified_count"] == 1


def test_audit_cache_is_project_scoped():
    from app.providers.cache_provider import _MEMORY_CACHE, cache_audit, get_cached_audit

    spec_hash, diff_hash = "s-scope", "d-scope"
    _MEMORY_CACHE.pop(f"audit:cache:proj-a:{spec_hash}:{diff_hash}", None)
    cache_audit("proj-a", spec_hash, diff_hash, {"id": "brief-a"})
    assert get_cached_audit("proj-a", spec_hash, diff_hash) == {"id": "brief-a"}
    assert get_cached_audit("proj-b", spec_hash, diff_hash) is None


def test_workflow_downgrades_hallucinated_evidence_end_to_end():
    """A covered verdict with invented evidence must not count toward coverage."""
    from app.core.workflow.pr_verification_graph import run_pr_verification_workflow

    hallucinated = [_verdict(evidenceSnippet="def invented_function(): pass")]
    alerts = [PRRiskAlert(kind="no_tests", severity="info", title="t", description="d")]

    with (
        patch(
            "app.core.workflow.pr_verification_graph.get_cached_audit", return_value=None
        ),
        patch("app.core.workflow.pr_verification_graph.cache_audit"),
        patch(
            "app.core.workflow.pr_verification_graph._run_stage2_verification",
            return_value=hallucinated,
        ),
        patch(
            "app.core.workflow.pr_verification_graph._run_stage3_risk_analysis",
            return_value=("Summary.", alerts),
        ),
    ):
        brief, is_cached = run_pr_verification_workflow(
            project_id="proj-evidence",
            user_id="dev-user",
            spec_text="R1: login",
            raw_diff=SAMPLE_DIFF,
            requirements=[
                {"id": "R1", "title": "Login API", "description": "d", "kind": "functional"}
            ],
            db=None,
        )

    assert is_cached is False
    assert brief.verdicts[0].status == "unclear"
    assert brief.verdicts[0].evidenceVerified is False
    assert brief.evidenceVerifiedCount == 0
    assert brief.evidenceUnverifiedCount == 1
    assert brief.coverageScore == 0
    assert brief.trustLevel == "low"
