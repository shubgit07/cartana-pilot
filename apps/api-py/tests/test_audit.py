"""Tests for the Audit + Coverage modules.

Covers audit run listing, latest audit retrieval, coverage link listing,
coverage link updates, and 404s. The audit engine itself requires pgvector
for full testing, so we test the CRUD contract here.
"""
from __future__ import annotations

from app.db.models import (
    AuditFinding,
    AuditFindingKind,
    AuditRun,
    AuditSeverity,
    CoverageLink,
    CoverageOrigin,
    CoverageStatus,
    Requirement,
    RequirementOrigin,
    RequirementState,
    Task,
    TaskOrigin,
    TaskState,
)
from tests.conftest import seed_project

AUDIT_RUN_KEYS = {
    "id", "projectId", "summary", "findingCount", "criticalCount",
    "warningCount", "infoCount", "createdAt",
}

COVERAGE_LINK_KEYS = {
    "id", "projectId", "requirementId", "requirementTitle", "taskId",
    "taskTitle", "status", "origin", "rationale", "createdAt", "updatedAt",
}


def _seed_audit_run(db, project, *, summary="Audit complete. 2/3 covered."):
    run = AuditRun(project_id=project.id, user_id=project.user_id, summary=summary)
    db.add(run)
    db.flush()
    db.add(AuditFinding(
        run_id=run.id,
        project_id=project.id,
        kind=AuditFindingKind.UNCOVERED_REQUIREMENT,
        severity=AuditSeverity.CRITICAL,
        message="Requirement X is not covered.",
    ))
    db.add(AuditFinding(
        run_id=run.id,
        project_id=project.id,
        kind=AuditFindingKind.ORPHAN_TASK,
        severity=AuditSeverity.INFO,
        message="Task Y is not linked.",
    ))
    db.commit()
    db.refresh(run)
    return run


def _seed_coverage_link(db, project, *, status=CoverageStatus.COVERED, origin=CoverageOrigin.AI_SUGGESTED):
    req = Requirement(
        project_id=project.id,
        user_id=project.user_id,
        title="Must support SSO",
        origin=RequirementOrigin.AI,
        state=RequirementState.ACCEPTED,
    )
    task = Task(
        project_id=project.id,
        user_id=project.user_id,
        title="Implement SSO",
        origin=TaskOrigin.USER,
        state=TaskState.ACCEPTED,
    )
    db.add_all([req, task])
    db.commit()
    db.refresh(req)
    db.refresh(task)

    link = CoverageLink(
        project_id=project.id,
        user_id=project.user_id,
        requirement_id=req.id,
        task_id=task.id,
        status=status,
        origin=origin,
        rationale="Test rationale",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def test_list_audit_runs_empty(client, db_session):
    project = seed_project(db_session)
    resp = client.get(f"/projects/{project.id}/audit/runs")
    assert resp.status_code == 200
    assert resp.json() == {"runs": []}


def test_list_audit_runs(client, db_session):
    project = seed_project(db_session)
    _seed_audit_run(db_session, project)
    resp = client.get(f"/projects/{project.id}/audit/runs")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert len(runs) == 1
    assert set(runs[0].keys()) == AUDIT_RUN_KEYS
    assert runs[0]["findingCount"] == 2
    assert runs[0]["criticalCount"] == 1
    assert runs[0]["infoCount"] == 1


def test_get_latest_audit(client, db_session):
    project = seed_project(db_session)
    _seed_audit_run(db_session, project, summary="First run")
    _seed_audit_run(db_session, project, summary="Second run")
    resp = client.get(f"/projects/{project.id}/audit/latest")
    assert resp.status_code == 200
    data = resp.json()["run"]
    assert data["summary"] == "Second run"
    assert len(data["findings"]) == 4  # 2 per run
    assert "coverageLinks" in data


def test_get_latest_audit_404(client, db_session):
    project = seed_project(db_session)
    resp = client.get(f"/projects/{project.id}/audit/latest")
    assert resp.status_code == 404


def test_list_coverage_links(client, db_session):
    project = seed_project(db_session)
    _seed_coverage_link(db_session, project)
    resp = client.get(f"/projects/{project.id}/coverage")
    assert resp.status_code == 200
    links = resp.json()["coverageLinks"]
    assert len(links) == 1
    assert set(links[0].keys()) == COVERAGE_LINK_KEYS


def test_update_coverage_link(client, db_session):
    project = seed_project(db_session)
    link = _seed_coverage_link(db_session, project, origin=CoverageOrigin.AI_SUGGESTED)
    resp = client.patch(
        f"/projects/{project.id}/coverage/{link.id}",
        json={"status": "partial", "rationale": "Only partially covered"},
    )
    assert resp.status_code == 200
    data = resp.json()["coverageLink"]
    assert data["status"] == "partial"
    assert data["origin"] == "user_confirmed"
    assert data["rationale"] == "Only partially covered"


def test_update_coverage_link_404(client, db_session):
    project = seed_project(db_session)
    resp = client.patch(
        f"/projects/{project.id}/coverage/nonexistent",
        json={"status": "covered"},
    )
    assert resp.status_code == 404
