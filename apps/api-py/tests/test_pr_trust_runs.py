"""Tests for verification-run persistence (Phase 3) and the runs API."""
from __future__ import annotations

from unittest.mock import patch

from sqlalchemy import func, select

from app.api.schemas.audit import PRRiskAlert, RequirementVerificationVerdict
from app.api.services import pr_trust_service
from app.db.models import EvidenceReference, RequirementVerdict, VerificationRun
from tests.conftest import seed_project
from tests.test_pr_verification_graph import SAMPLE_DIFF

REQUIREMENTS = [
    {"id": "R1", "title": "User registration", "description": "JWT auth", "kind": "functional"},
]


def _fake_stages():
    verdicts = [
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
    alerts = [
        PRRiskAlert(
            kind="no_tests",
            severity="info",
            title="No tests in PR",
            description="Add test coverage.",
            affectedFiles=["app/routes/auth.py"],
        )
    ]
    return (
        patch(
            "app.core.workflow.pr_verification_graph._run_stage2_verification",
            return_value=verdicts,
        ),
        patch(
            "app.core.workflow.pr_verification_graph._run_stage3_risk_analysis",
            return_value=(90, "high", "High trust summary", alerts),
        ),
    )


def test_workflow_persists_run_verdicts_and_evidence(db_session):
    project = seed_project(db_session)
    stage2, stage3 = _fake_stages()
    with stage2, stage3:
        brief, is_cached = pr_trust_service.verify_pr_and_generate_trust_brief(
            db_session,
            user_id=project.user_id,
            project_id=project.id,
            input_data=__import__("app.api.schemas.audit", fromlist=["VerifyPRInput"]).VerifyPRInput(
                specText="R1: User registration and login with JWT.",
                rawDiff=SAMPLE_DIFF,
            ),
        )
    assert is_cached is False

    runs = db_session.execute(select(VerificationRun)).scalars().all()
    assert len(runs) == 1
    assert brief.id == runs[0].id  # Brief links to its persisted run.
    assert runs[0].status.value == "succeeded"

    verdicts = db_session.execute(select(RequirementVerdict)).scalars().all()
    assert len(verdicts) == 1
    assert verdicts[0].verdict.value == "satisfied"

    evidence = db_session.execute(select(EvidenceReference)).scalars().all()
    assert len(evidence) == 1
    assert evidence[0].quote != ""

    # Runs API reads back the same data.
    summaries = pr_trust_service.list_verification_runs(
        db_session, project_id=project.id, user_id=project.user_id
    )
    assert len(summaries) == 1
    assert summaries[0]["coverageScore"] == 90
    assert summaries[0]["coveredCount"] == 1

    fetched = pr_trust_service.get_verification_brief(
        db_session, project_id=project.id, user_id=project.user_id, run_id=runs[0].id
    )
    assert fetched is not None
    assert fetched.coverageScore == 90


def test_rerun_reuses_requirement_revision(db_session):
    from app.api.schemas.audit import VerifyPRInput
    from app.db.models import RequirementRevision

    project = seed_project(db_session)
    for _ in range(2):
        stage2, stage3 = _fake_stages()
        with (
            stage2,
            stage3,
            patch("app.core.workflow.pr_verification_graph.get_cached_audit", return_value=None),
            patch("app.core.workflow.pr_verification_graph.cache_audit"),
        ):
            pr_trust_service.verify_pr_and_generate_trust_brief(
                db_session,
                user_id=project.user_id,
                project_id=project.id,
                input_data=VerifyPRInput(
                    specText="R1: User registration and login with JWT.",
                    rawDiff=SAMPLE_DIFF,
                ),
            )
    revisions = db_session.execute(select(func.count()).select_from(RequirementRevision)).scalar_one()
    assert revisions == 1  # Same text pins the same revision across runs.
    runs = db_session.execute(select(func.count()).select_from(VerificationRun)).scalar_one()
    assert runs == 2  # Each verification is its own audit-trail entry.
