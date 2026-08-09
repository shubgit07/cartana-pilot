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

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.audit import (
    AuditFindingSummary,
    AuditRunDetail,
    AuditRunSummary,
    ChangedFileSummary,
    CoverageLinkSummary,
    PRRiskAlert,
    PRTrustBrief,
    RequirementVerificationVerdict,
    UpdateCoverageLink,
    VerifyPRInput,
)
from app.api.services.project_service import get_owned_project
from app.core.clean_text import clean_document_text
from app.core.diff_parser import parse_unified_diff
from app.core.errors import LLMServiceError, NotFoundError, ValidationError
from app.db.models import (
    AuditFinding,
    AuditFindingKind,
    AuditRun,
    AuditSeverity,
    CoverageLink,
    CoverageOrigin,
    Requirement,
    RequirementState,
    Task,
    TaskState,
)
from app.providers.ai_provider import (
    AIAuditCoverageInput,
    AIChatInput,
    AIRiskSummaryInput,
    CoverageJudgment,
    _safe_json_loads,
    get_ai_provider,
)
from app.providers.cache_provider import cache_audit, get_cached_audit
from app.providers.embedding_provider import get_embedding_provider
from app.providers.prompts.pr_audit import (
    build_pr_risk_summary_prompt,
    build_pr_verification_prompt,
)

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Dot product of two L2-normalized vectors (= cosine similarity)."""
    return sum(x * y for x, y in zip(a, b))


def _overall_status(statuses: list[str]) -> str:
    """Aggregate per-task judgments into a single coverage status."""
    if not statuses or all(s == "missing" for s in statuses):
        return "missing"
    if any(s == "covered" for s in statuses):
        return "covered"
    if any(s == "partial" for s in statuses):
        return "partial"
    return "unclear"


def _status_rank(status: str) -> int:
    return {"covered": 3, "partial": 2, "unclear": 1, "missing": 0}.get(status, 0)


def _select_candidate_tasks(req_text: str, tasks: list[Task], top_k: int = 5) -> list[Task]:
    """Rank tasks by embedding cosine similarity to the requirement text.

    Pure retrieval (no DB writes, no LLM). No token-overlap fallback: if
    embeddings fail, ``LLMServiceError`` is raised so the caller never silently
    audits against a degraded candidate set.
    """
    if not tasks:
        return []
    if len(tasks) <= top_k:
        return list(tasks)

    task_texts = [f"{t.title} {t.description or ''}".strip() for t in tasks]
    try:
        provider = get_embedding_provider()
        vectors = provider.embed([req_text.strip(), *task_texts])
    except Exception as e:
        logger.error("Audit: embedding failed during candidate selection: %s", e)
        raise LLMServiceError(f"Embedding unavailable for coverage audit: {e}") from e

    if len(vectors) != 1 + len(tasks):
        raise LLMServiceError(
            f"Embedding provider returned {len(vectors)} vectors for {1 + len(tasks)} texts"
        )

    req_vec = vectors[0]
    scored = [
        (task, _cosine_similarity(req_vec, task_vec))
        for task, task_vec in zip(tasks, vectors[1:])
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [task for task, _ in scored[:top_k]]


def _judge_coverage(provider, input: AIAuditCoverageInput) -> list[CoverageJudgment]:
    """Run one coverage judgment, isolating LLM failures (returns an 'unclear' judgment)."""
    try:
        return provider.audit_coverage(input).judgments
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit: LLM judgment failed for req %r: %s", input.requirement.get("title"), e)
        return [CoverageJudgment(status="unclear", rationale="LLM judgment unavailable.")]


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


def get_latest_audit(db: Session, user_id: str, project_id: str) -> AuditRunDetail | None:
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
    if changes.get("status"):
        link.status = changes["status"]
    if "rationale" in changes:
        link.rationale = changes["rationale"]
    link.origin = CoverageOrigin.USER_CONFIRMED

    db.commit()
    db.refresh(link)
    return _to_coverage_link_summary(link)


# ---- Core audit engine (called by the ARQ task) ----


def promote_suggestions_to_accepted(
    db: Session, user_id: str, project_id: str
) -> dict[str, int]:
    """Promote AI-suggested requirements/tasks to ``accepted`` for audit.

    Extraction persists LLM output as ``suggested`` so a human can review it
    before it becomes effective. The audit engine only evaluates requirements
    and tasks that are not in ``rejected``/``suggested`` state, so an
    unattended pipeline (or CLI driver) must promote suggestions first.

    Returns counts of promoted rows: ``{"requirements": int, "tasks": int}``.
    """
    requirements = (
        db.execute(
            select(Requirement).where(
                Requirement.project_id == project_id,
                Requirement.user_id == user_id,
                Requirement.state == RequirementState.SUGGESTED,
            )
        )
        .scalars()
        .all()
    )
    tasks = (
        db.execute(
            select(Task).where(
                Task.project_id == project_id,
                Task.user_id == user_id,
                Task.state == TaskState.SUGGESTED,
            )
        )
        .scalars()
        .all()
    )

    for requirement in requirements:
        requirement.state = RequirementState.ACCEPTED
    for task in tasks:
        task.state = TaskState.ACCEPTED

    if requirements or tasks:
        db.commit()

    return {"requirements": len(requirements), "tasks": len(tasks)}


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

    findings_to_create: list[dict[str, str | None]] = []
    coverage_links_to_create: list[dict[str, str]] = []
    req_coverage_status: list[dict[str, str]] = []

    # Pass 1: select candidate tasks per requirement (embedding cosine retrieval, pure)
    plan: list[tuple[Requirement, list[str], list[dict[str, str]]]] = []
    for req in requirements:
        req_text = f"{req.title} {req.description or ''}"
        candidate_tasks = _select_candidate_tasks(req_text, list(tasks), top_k=5)
        plan.append((
            req,
            [t.id for t in candidate_tasks],
            [{"title": t.title, "description": t.description or ""} for t in candidate_tasks],
        ))

    # Pass 2: LLM judgments. Cloudflare tolerates parallel calls (300 req/min);
    # other providers (Groq free TPM, stub) stay sequential to avoid rate limits.
    audit_inputs = [
        AIAuditCoverageInput(
            requirement={"title": req.title, "description": req.description or ""},
            candidateTasks=candidate_tasks,
        )
        for req, _, candidate_tasks in plan
    ]

    if getattr(provider, "parallel_audit", False):
        with ThreadPoolExecutor(max_workers=8) as pool:
            judgments_list = list(pool.map(lambda inp: _judge_coverage(provider, inp), audit_inputs))
    else:
        judgments_list = [_judge_coverage(provider, inp) for inp in audit_inputs]

    # Pass 3: confidence-triggered re-retrieval. A requirement judged `missing` or
    # `unclear` gets one wider re-search (top_k * 2) and a single re-classification;
    # the better verdict wins and `reRetrieved` is recorded. Bounded: exactly one re-check.
    reretrieved: list[bool] = []
    for i, (req, candidate_task_ids, candidate_tasks) in enumerate(plan):
        overall = _overall_status([j.status for j in judgments_list[i]])
        if overall not in ("missing", "unclear"):
            reretrieved.append(False)
            continue

        wider = _select_candidate_tasks(f"{req.title} {req.description or ''}", list(tasks), top_k=10)
        if not wider:
            reretrieved.append(False)
            continue

        retry_judgments = _judge_coverage(provider, AIAuditCoverageInput(
            requirement={"title": req.title, "description": req.description or ""},
            candidateTasks=[{"title": t.title, "description": t.description or ""} for t in wider],
        ))
        retry_overall = _overall_status([j.status for j in retry_judgments])

        if _status_rank(retry_overall) > _status_rank(overall):
            plan[i] = (
                req,
                [t.id for t in wider],
                [{"title": t.title, "description": t.description or ""} for t in wider],
            )
            judgments_list[i] = retry_judgments
            reretrieved.append(True)
        else:
            reretrieved.append(False)

    logger.info(
        "Audit: re-retrieval pass rescued %d requirement(s)",
        sum(1 for r in reretrieved if r),
    )

    # Pass 4: derive coverage status, links, and findings (DB writes stay here)
    for (req, candidate_task_ids, _), judgments in zip(plan, judgments_list):
        # Determine overall coverage status
        statuses = [j.status for j in judgments]
        overall_status = _overall_status(statuses)

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


# ---- Phase 4: Decomposed PR Trust Brief Engine ----


def _parse_verdicts(raw_json: str | None, *, label: str) -> list[dict[str, Any]]:
    """Parse a Stage 2 verdicts payload; [] when empty or unparseable."""
    if not raw_json:
        return []
    try:
        parsed = _safe_json_loads(raw_json, label=label)
    except Exception as e:  # noqa: BLE001
        logger.warning("%s output was not valid JSON: %s", label, e)
        return []
    if isinstance(parsed, dict):
        return parsed.get("verdicts", [])
    return []


def _run_stage2_verification(
    provider,
    reqs: list[dict[str, Any]],
    changed_files: list[dict[str, Any]],
    diff_hunks: str,
    *,
    diagnostics: dict[str, Any] | None = None,
) -> list[RequirementVerificationVerdict]:
    """Stage 2: Strict Code Verifier (LLM Call 1)."""
    system_prompt, user_prompt = build_pr_verification_prompt(reqs, changed_files, diff_hunks)

    def _record(key: str, value: object) -> None:
        if diagnostics is not None:
            diagnostics[key] = value

    verdicts_data: list[dict[str, Any]] = []

    if hasattr(provider, "_structured"):
        raw_json: str | None = None
        try:
            raw_json = provider._structured(system_prompt, user_prompt, max_tokens=6000, temperature=0.1)
            _record("structured", raw_json)
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 2 structured LLM call failed: %s", e)
            _record("structured_error", str(e))
        verdicts_data = _parse_verdicts(raw_json, label="Stage 2 Verification")

    if not verdicts_data and hasattr(provider, "chat"):
        try:
            chat_out = provider.chat(AIChatInput(question=f"{system_prompt}\n\n{user_prompt}", history=[], passages=[]))
            _record("chat", chat_out.answer)
            verdicts_data = _parse_verdicts(chat_out.answer, label="Stage 2 Verification (chat)")
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 2 chat LLM call failed: %s", e)
            _record("chat_error", str(e))

    if verdicts_data:
        verdicts: list[RequirementVerificationVerdict] = []
        for v in verdicts_data:
            status_val = v.get("status", "unclear")
            if status_val not in ("covered", "partial", "missing", "unclear"):
                status_val = "unclear"
            conf_val = v.get("confidence", "high")
            if conf_val not in ("high", "medium", "low"):
                conf_val = "high"

            verdicts.append(RequirementVerificationVerdict(
                reqId=str(v.get("reqId", "R?")),
                title=str(v.get("title", "")),
                status=status_val,
                confidence=conf_val,
                evidenceFile=v.get("evidenceFile"),
                evidenceSnippet=v.get("evidenceSnippet"),
                rationale=str(v.get("rationale", "")),
            ))
        return verdicts

    # No LLM verdicts were produced. Fail loudly — never degrade to keyword
    # heuristics (the verifier must be LLM-driven).
    raise LLMServiceError(
        "Stage 2 verification failed: the LLM did not return valid verdicts. "
        "Check that an LLM provider is configured (LLM_PROVIDER != stub) and "
        "that the provider's structured output is parseable."
    )


def _parse_risk_analysis(raw_json: str | None, *, label: str) -> dict[str, Any] | None:
    """Parse a Stage 3 risk/trust payload; None when empty or unparseable."""
    if not raw_json:
        return None
    try:
        parsed = _safe_json_loads(raw_json, label=label)
    except Exception as e:  # noqa: BLE001
        logger.warning("%s output was not valid JSON: %s", label, e)
        return None
    if isinstance(parsed, dict) and "coverageScore" in parsed:
        return parsed
    return None


def _run_stage3_risk_analysis(
    provider,
    verdicts: list[RequirementVerificationVerdict],
    changed_files: list[dict[str, Any]],
    *,
    diagnostics: dict[str, Any] | None = None,
) -> tuple[int, str, str, list[PRRiskAlert]]:
    """Stage 3: Risk, Security & Trust Analyst (LLM Call 2)."""
    verdicts_dict = [v.model_dump() for v in verdicts]
    system_prompt, user_prompt = build_pr_risk_summary_prompt(verdicts_dict, changed_files)

    def _record(key: str, value: object) -> None:
        if diagnostics is not None:
            diagnostics[key] = value

    parsed: dict[str, Any] | None = None

    if hasattr(provider, "_structured"):
        raw_json: str | None = None
        try:
            raw_json = provider._structured(system_prompt, user_prompt, max_tokens=3000, temperature=0.2)
            _record("structured", raw_json)
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 3 structured LLM call failed: %s", e)
            _record("structured_error", str(e))
        parsed = _parse_risk_analysis(raw_json, label="Stage 3 Risk Analysis")

    if parsed is None and hasattr(provider, "chat"):
        try:
            chat_out = provider.chat(AIChatInput(question=f"{system_prompt}\n\n{user_prompt}", history=[], passages=[]))
            _record("chat", chat_out.answer)
            parsed = _parse_risk_analysis(chat_out.answer, label="Stage 3 Risk Analysis (chat)")
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 3 chat LLM call failed: %s", e)
            _record("chat_error", str(e))

    if parsed is not None:
        alerts: list[PRRiskAlert] = []
        for a in parsed.get("riskAlerts", []):
            kind_val = a.get("kind", "security_gap")
            if kind_val not in ("missing_backend_check", "no_tests", "scope_creep", "security_gap", "error_handling"):
                kind_val = "security_gap"
            sev_val = a.get("severity", "warning")
            if sev_val not in ("critical", "warning", "info"):
                sev_val = "warning"
            alerts.append(PRRiskAlert(
                kind=kind_val,
                severity=sev_val,
                title=str(a.get("title", "")),
                description=str(a.get("description", "")),
                affectedFiles=[str(f) for f in a.get("affectedFiles", [])],
            ))

        trust_val = str(parsed.get("trustLevel", "medium")).lower()
        if trust_val not in ("high", "medium", "low"):
            trust_val = "medium"

        return (
            int(parsed.get("coverageScore", 0)),
            trust_val,
            str(parsed.get("summary", "")),
            alerts,
        )

    # No LLM risk analysis was produced. Fail loudly — never fabricate a trust
    # score from local heuristics.
    raise LLMServiceError(
        "Stage 3 risk analysis failed: the LLM did not return a valid trust "
        "brief. Check that an LLM provider is configured (LLM_PROVIDER != stub) "
        "and that the provider's structured output is parseable."
    )


def verify_pr_and_generate_trust_brief(
    db: Session,
    user_id: str,
    project_id: str,
    input_data: VerifyPRInput,
) -> tuple[PRTrustBrief, bool]:
    """Decomposed PR Trust Brief Engine.

    Executes:
    1. Upstash Redis / In-memory deduplication check (key: sha256(spec + diff)).
    2. Deterministic diff parsing & noise stripping (0 LLM cost).
    3. Stage 2: Strict Code Verifier LLM Call.
    4. Stage 3: Risk, Security & Trust Analyst LLM Call.
    5. Database record persistence + cache write.
    """
    get_owned_project(db, user_id, project_id)

    spec_raw = (input_data.specText or "").strip()
    diff_raw = (input_data.rawDiff or "").strip()
    pr_url = (input_data.githubPrUrl or "").strip()

    # 1. Fetch GitHub diff if URL provided
    if pr_url and not diff_raw:
        clean_url = pr_url.rstrip("/")
        diff_url = f"{clean_url}.diff" if "github.com" in clean_url and "/pull/" in clean_url and not clean_url.endswith(".diff") else clean_url
        try:
            resp = httpx.get(
                diff_url,
                headers={"User-Agent": "Cartana-PR-Verifier", "Accept": "text/plain"},
                follow_redirects=True,
                timeout=15.0,
            )
            if resp.status_code == 200:
                diff_raw = resp.text
            else:
                raise ValidationError(f"Failed to fetch GitHub PR diff from {diff_url} (HTTP {resp.status_code})")
        except ValidationError:
            raise
        except Exception as e:
            logger.warning("Failed to fetch PR diff from URL %s: %s", pr_url, e)
            raise ValidationError(f"Could not download GitHub PR diff: {e}") from e

    if not diff_raw:
        raise ValidationError("No git diff provided. Please paste a unified diff or provide a valid GitHub PR URL.")

    # 2. Check Deduplication Cache (Upstash Redis)
    spec_hash = hashlib.sha256(spec_raw.encode("utf-8")).hexdigest()[:16]
    diff_hash = hashlib.sha256(diff_raw.encode("utf-8")).hexdigest()[:16]
    cached = get_cached_audit(spec_hash, diff_hash)
    if cached:
        logger.info("PR Trust Brief: Cache hit for spec_hash=%s, diff_hash=%s", spec_hash, diff_hash)
        return PRTrustBrief(**cached), True

    # 3. Parse Requirements via LLM & Transcript Cleaner
    reqs: list[dict[str, Any]] = []
    if spec_raw:
        from app.api.services.input_service import extract_requirements_with_llm

        cleaned_spec = clean_document_text(spec_raw)
        extracted = extract_requirements_with_llm(cleaned_spec)
        for item in extracted:
            reqs.append({
                "id": item.req_id,
                "title": item.title,
                "description": item.description,
                "kind": item.kind,
            })
    else:
        db_reqs = db.execute(
            select(Requirement)
            .where(
                Requirement.project_id == project_id,
                Requirement.state != RequirementState.REJECTED,
            )
            .order_by(Requirement.created_at.asc())
        ).scalars().all()
        for i, r in enumerate(db_reqs, start=1):
            reqs.append({"id": f"R{i}", "title": r.title, "description": r.description or r.title})

    if not reqs:
        raise ValidationError("No requirements found. Please provide a spec text or upload a project document.")

    # 4. Deterministic Diff Parsing & Noise Filtering (Stage 1)
    parsed_diff = parse_unified_diff(diff_raw)
    changed_files_summary = [
        ChangedFileSummary(
            filename=f.filename,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
        )
        for f in parsed_diff.files
    ]
    changed_files_dict = [f.model_dump() for f in changed_files_summary]

    # 5. Stage 2: Strict Code Verification (LLM Call 1)
    provider = get_ai_provider()
    verdicts = _run_stage2_verification(
        provider,
        reqs,
        changed_files_dict,
        parsed_diff.compressed_text,
    )

    # 6. Stage 3: Risk, Security & Trust Scoring (LLM Call 2)
    score, trust_level, summary_text, risk_alerts = _run_stage3_risk_analysis(
        provider,
        verdicts,
        changed_files_dict,
    )

    covered_count = sum(1 for v in verdicts if v.status == "covered")
    partial_count = sum(1 for v in verdicts if v.status == "partial")
    missing_count = sum(1 for v in verdicts if v.status == "missing")

    # 7. Persist to PostgreSQL (AuditRun + AuditFinding)
    audit_run = AuditRun(
        project_id=project_id,
        user_id=user_id,
        summary=summary_text,
    )
    db.add(audit_run)
    db.flush()

    for alert in risk_alerts:
        sev = AuditSeverity.WARNING
        if alert.severity == "critical":
            sev = AuditSeverity.CRITICAL
        elif alert.severity == "info":
            sev = AuditSeverity.INFO

        db.add(AuditFinding(
            run_id=audit_run.id,
            project_id=project_id,
            kind=AuditFindingKind.OTHER,
            severity=sev,
            message=f"[{alert.title}] {alert.description}",
        ))
    db.commit()

    brief_id = audit_run.id
    now_iso = datetime.now(UTC).isoformat()
    brief = PRTrustBrief(
        id=brief_id,
        projectId=project_id,
        title=f"PR Trust Brief ({trust_level.upper()} Trust)",
        coverageScore=score,
        trustLevel=trust_level,  # type: ignore[arg-type]
        summary=summary_text,
        totalRequirements=len(reqs),
        coveredCount=covered_count,
        partialCount=partial_count,
        missingCount=missing_count,
        verdicts=verdicts,
        riskAlerts=risk_alerts,
        changedFilesSummary=changed_files_summary,
        createdAt=now_iso,
    )

    # 8. Cache in Upstash / Memory Cache for 24 hours
    cache_audit(spec_hash, diff_hash, brief.model_dump(), ttl_seconds=86400)

    logger.info(
        "PR Trust Brief: Verification complete for project_id=%s (Score=%d%%, Trust=%s, Findings=%d)",
        project_id,
        score,
        trust_level,
        len(risk_alerts),
    )
    return brief, False

