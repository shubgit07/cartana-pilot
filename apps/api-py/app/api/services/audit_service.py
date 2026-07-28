"""Audit module — coverage audit engine + coverage link management.

Port of ``apps/api/src/modules/audit/service.ts``.

Flow:
1. Fetch effective requirements (accepted + user-created, not rejected/suggested)
2. Fetch effective tasks (same criteria)
3. For each requirement: find candidate tasks via token overlap, call AI auditCoverage
4. Write/update CoverageLinks (preserve user-confirmed links as ground truth)
5. Generate AuditFindings (uncovered, partial, vague, orphan)
6. Generate risk summary via AIProvider
7. Create AuditRun with summary + findings
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.audit import (
    AuditFindingSummary,
    AuditRunDetail,
    AuditRunSummary,
    CoverageLinkSummary,
    UpdateCoverageLink,
)
from app.api.services.project_service import get_owned_project
from app.core.errors import NotFoundError
from app.db.models import (
    AuditFinding,
    AuditFindingKind,
    AuditRun,
    AuditSeverity,
    CoverageLink,
    CoverageOrigin,
    CoverageStatus,
    Requirement,
    Task,
)
from app.providers.ai_provider import (
    AIAuditCoverageInput,
    AIRiskSummaryInput,
    get_ai_provider,
)

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [t for t in cleaned.split() if len(t) > 3]


# ---- DTO helpers ----


def _to_coverage_link_summary(link: CoverageLink) -> CoverageLinkSummary:
    return CoverageLinkSummary.from_model(link)


def _to_finding_summary(finding: AuditFinding) -> AuditFindingSummary:
    return AuditFindingSummary.from_model(finding)


def _to_run_summary(run: AuditRun, findings: list[AuditFinding]) -> AuditRunSummary:
    return AuditRunSummary.from_model(run, findings)


# ---- Public API (used by routes) ----


def list_audit_runs(db: Session, user_id: str, project_id: str) -> list[AuditRunSummary]:
    get_owned_project(db, user_id, project_id)

    runs = db.execute(
        select(AuditRun)
        .where(AuditRun.project_id == project_id, AuditRun.user_id == user_id)
        .order_by(AuditRun.created_at.desc())
    ).scalars().all()

    result: list[AuditRunSummary] = []
    for run in runs:
        findings = db.execute(
            select(AuditFinding).where(AuditFinding.run_id == run.id)
        ).scalars().all()
        result.append(_to_run_summary(run, list(findings)))
    return result


def get_latest_audit(db: Session, user_id: str, project_id: str) -> Optional[AuditRunDetail]:
    get_owned_project(db, user_id, project_id)

    run = db.execute(
        select(AuditRun)
        .where(AuditRun.project_id == project_id, AuditRun.user_id == user_id)
        .order_by(AuditRun.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if run is None:
        return None

    findings = (
        db.execute(
            select(AuditFinding)
            .where(AuditFinding.run_id == run.id)
            .order_by(AuditFinding.severity.asc(), AuditFinding.created_at.desc())
        )
        .scalars()
        .all()
    )

    coverage_links = (
        db.execute(
            select(CoverageLink)
            .where(CoverageLink.project_id == project_id, CoverageLink.user_id == user_id)
            .order_by(CoverageLink.requirement_id.asc())
        )
        .scalars()
        .all()
    )

    summary = _to_run_summary(run, list(findings))
    return AuditRunDetail(
        **summary.model_dump(),
        findings=[_to_finding_summary(f) for f in findings],
        coverageLinks=[_to_coverage_link_summary(c) for c in coverage_links],
    )


def list_coverage_links(db: Session, user_id: str, project_id: str) -> list[CoverageLinkSummary]:
    get_owned_project(db, user_id, project_id)

    links = (
        db.execute(
            select(CoverageLink)
            .where(CoverageLink.project_id == project_id, CoverageLink.user_id == user_id)
            .order_by(CoverageLink.requirement_id.asc(), CoverageLink.status.asc())
        )
        .scalars()
        .all()
    )
    return [_to_coverage_link_summary(l) for l in links]


def update_coverage_link(
    db: Session,
    user_id: str,
    project_id: str,
    link_id: str,
    payload: UpdateCoverageLink,
) -> CoverageLinkSummary:
    link = db.execute(
        select(CoverageLink).where(
            CoverageLink.id == link_id,
            CoverageLink.project_id == project_id,
            CoverageLink.user_id == user_id,
        )
    ).scalar_one_or_none()
    if link is None:
        raise NotFoundError("Coverage link not found")

    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"]:
        link.status = changes["status"]
    if "rationale" in changes:
        link.rationale = changes["rationale"]
    link.origin = CoverageOrigin.USER_CONFIRMED

    db.commit()
    db.refresh(link)
    return _to_coverage_link_summary(link)


# ---- Core audit engine (called by the Celery task) ----


def run_audit(db: Session, user_id: str, project_id: str) -> str:
    """Run the full coverage audit and create an AuditRun. Returns the run ID."""
    get_owned_project(db, user_id, project_id)

    provider = get_ai_provider()

    # 1. Fetch effective requirements (not rejected, not suggested)
    requirements = (
        db.execute(
            select(Requirement)
            .where(
                Requirement.project_id == project_id,
                Requirement.user_id == user_id,
                Requirement.state.notin_(["rejected", "suggested"]),
            )
        )
        .scalars()
        .all()
    )

    # 2. Fetch effective tasks
    tasks = (
        db.execute(
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.user_id == user_id,
                Task.state.notin_(["rejected", "suggested"]),
            )
        )
        .scalars()
        .all()
    )

    logger.info("Audit: starting (project_id=%s, reqs=%d, tasks=%d)", project_id, len(requirements), len(tasks))

    findings_to_create: list[dict[str, Optional[str]]] = []
    coverage_links_to_create: list[dict[str, str]] = []
    req_coverage_status: list[dict[str, str]] = []

    for req in requirements:
        req_text = f"{req.title} {req.description or ''}"
        candidate_task_ids: list[str] = []
        candidate_tasks: list[dict[str, str]] = []

        if tasks:
            if len(tasks) > 5:
                # Token overlap to find top-5 candidates
                req_tokens = set(_tokenize(req_text))
                scored = [
                    (t, sum(1 for tok in _tokenize(f"{t.title} {t.description or ''}") if tok in req_tokens))
                    for t in tasks
                ]
                scored.sort(key=lambda x: x[1], reverse=True)
                top5 = scored[:5]
                candidate_tasks = [{"title": t.title, "description": t.description or ""} for t, _ in top5]
                candidate_task_ids = [t.id for t, _ in top5]
            else:
                candidate_tasks = [{"title": t.title, "description": t.description or ""} for t in tasks]
                candidate_task_ids = [t.id for t in tasks]

        # 3c. Call AI provider for judgment
        try:
            result = provider.audit_coverage(AIAuditCoverageInput(
                requirement={"title": req.title, "description": req.description or ""},
                candidateTasks=candidate_tasks,
            ))
            judgments = result.judgments
        except Exception as e:  # noqa: BLE001
            logger.warning("Audit: LLM judgment failed for req %s: %s", req.id, e)
            from app.providers.ai_provider import CoverageJudgment
            judgments = [CoverageJudgment(status="unclear", rationale="LLM judgment unavailable.")]

        # Determine overall coverage status
        statuses = [j.status for j in judgments]
        if not statuses or all(s == "missing" for s in statuses):
            overall_status = "missing"
        elif any(s == "covered" for s in statuses):
            overall_status = "covered"
        elif any(s == "partial" for s in statuses):
            overall_status = "partial"
        else:
            overall_status = "unclear"

        req_coverage_status.append({"title": req.title, "status": overall_status})

        # 3d. Write coverage links (preserve user-confirmed)
        for i, judgment in enumerate(judgments):
            if i >= len(candidate_task_ids):
                break
            task_id = candidate_task_ids[i]

            existing = db.execute(
                select(CoverageLink).where(
                    CoverageLink.requirement_id == req.id,
                    CoverageLink.task_id == task_id,
                )
            ).scalar_one_or_none()

            if existing and existing.origin == CoverageOrigin.USER_CONFIRMED:
                continue

            coverage_links_to_create.append({
                "requirementId": req.id,
                "taskId": task_id,
                "status": judgment.status,
                "rationale": judgment.rationale,
            })

        # 4. Generate findings
        if overall_status == "missing":
            findings_to_create.append({
                "kind": "uncovered_requirement",
                "severity": "critical",
                "message": f'Requirement "{req.title}" is not covered by any task.',
                "requirementId": req.id,
                "taskId": None,
            })
        elif overall_status == "partial":
            findings_to_create.append({
                "kind": "partial_coverage",
                "severity": "warning",
                "message": f'Requirement "{req.title}" is only partially covered.',
                "requirementId": req.id,
                "taskId": None,
            })
        elif overall_status == "unclear":
            findings_to_create.append({
                "kind": "partial_coverage",
                "severity": "info",
                "message": f'Requirement "{req.title}" has unclear coverage — tasks may not be related.',
                "requirementId": req.id,
                "taskId": None,
            })

        # Vague requirement detection
        if len(req.title) < 10 and (not req.description or len(req.description) < 20):
            findings_to_create.append({
                "kind": "vague_requirement",
                "severity": "warning",
                "message": f'Requirement "{req.title}" is too vague — add more detail.',
                "requirementId": req.id,
                "taskId": None,
            })

    # Orphan task detection
    for task in tasks:
        if not task.requirement_id:
            has_coverage = any(c["taskId"] == task.id for c in coverage_links_to_create)
            if not has_coverage:
                existing_link = db.execute(
                    select(CoverageLink).where(
                        CoverageLink.task_id == task.id,
                        CoverageLink.project_id == project_id,
                    )
                ).scalar_one_or_none()
                if not existing_link:
                    findings_to_create.append({
                        "kind": "orphan_task",
                        "severity": "info",
                        "message": f'Task "{task.title}" is not linked to any requirement.',
                        "requirementId": None,
                        "taskId": task.id,
                    })

    # 5. Generate risk summary
    try:
        risk_result = provider.risk_summary(AIRiskSummaryInput(
            requirements=req_coverage_status,
            findings=[
                {"kind": f["kind"], "severity": f["severity"], "message": f["message"]}
                for f in findings_to_create
            ],
        ))
        summary_text = risk_result.summary
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit: risk summary generation failed: %s", e)
        covered = sum(1 for r in req_coverage_status if r["status"] == "covered")
        missing = sum(1 for r in req_coverage_status if r["status"] == "missing")
        summary_text = (
            f"Coverage audit complete. {covered}/{len(req_coverage_status)} requirements covered, "
            f"{missing} missing. {len(findings_to_create)} findings."
        )

    # 6. Create AuditRun + findings
    audit_run = AuditRun(
        project_id=project_id,
        user_id=user_id,
        summary=summary_text,
    )
    db.add(audit_run)
    db.flush()

    for f in findings_to_create:
        finding = AuditFinding(
            run_id=audit_run.id,
            project_id=project_id,
            kind=f["kind"],
            severity=f["severity"],
            message=f["message"],
            requirement_id=f.get("requirementId"),
            task_id=f.get("taskId"),
        )
        db.add(finding)

    db.commit()

    # Write coverage links (delete old AI-suggested, preserve user-confirmed)
    if coverage_links_to_create:
        db.query(CoverageLink).filter(
            CoverageLink.project_id == project_id,
            CoverageLink.origin == CoverageOrigin.AI_SUGGESTED,
        ).delete(synchronize_session=False)
        db.commit()

        for cl in coverage_links_to_create:
            existing = db.execute(
                select(CoverageLink).where(
                    CoverageLink.requirement_id == cl["requirementId"],
                    CoverageLink.task_id == cl["taskId"],
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(CoverageLink(
                    project_id=project_id,
                    user_id=user_id,
                    requirement_id=cl["requirementId"],
                    task_id=cl["taskId"],
                    status=cl["status"],
                    origin=CoverageOrigin.AI_SUGGESTED,
                    rationale=cl["rationale"],
                ))
        db.commit()

    logger.info("Audit: complete (project_id=%s, run_id=%s, findings=%d)", project_id, audit_run.id, len(findings_to_create))
    return audit_run.id
