"""Focused PR Trust Brief orchestration service."""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.audit import PRTrustBrief, VerifyPRInput
from app.api.services.project_service import get_owned_project
from app.config import get_settings
from app.core.errors import ValidationError
from app.db.models import (
    EvidenceKind,
    EvidenceReference,
    RepositoryFile,
    Requirement,
    RequirementRevision,
    RequirementState,
    RequirementVerdict,
    RunStatus,
    SnapshotKind,
    VerificationRun,
    VerificationVerdict,
)

# Provider seam for the orchestration layer (mirrors input_service): resolved
# here so the recorded run provenance reflects the active LLM entrypoint.
from app.providers.ai_provider import get_ai_provider

logger = logging.getLogger(__name__)

VERIFIER_VERSION = "pr-graph-v1"

_STATUS_TO_VERDICT = {
    "covered": VerificationVerdict.SATISFIED,
    "partial": VerificationVerdict.PARTIAL,
    "missing": VerificationVerdict.NOT_SATISFIED,
    "unclear": VerificationVerdict.INCONCLUSIVE,
}
_CONFIDENCE_TO_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.3}


def verify_pr_and_generate_trust_brief(
    db: Session,
    user_id: str,
    project_id: str,
    input_data: VerifyPRInput,
) -> tuple[PRTrustBrief, bool]:
    """Verify a supplied diff without fabricating immutable Phase 0 records."""
    from app.core.workflow.pr_verification_graph import run_pr_verification_workflow

    get_owned_project(db, user_id, project_id)
    spec_raw = (input_data.specText or "").strip()
    diff_raw = (input_data.rawDiff or "").strip()
    pr_url = (input_data.githubPrUrl or "").strip()

    if pr_url and not diff_raw:
        clean_url = pr_url.rstrip("/")
        diff_url = (
            f"{clean_url}.diff"
            if "github.com" in clean_url
            and "/pull/" in clean_url
            and not clean_url.endswith(".diff")
            else clean_url
        )
        try:
            response = httpx.get(
                diff_url,
                headers={"User-Agent": "Cartana-PR-Verifier", "Accept": "text/plain"},
                follow_redirects=True,
                timeout=15.0,
            )
        except Exception as exc:
            raise ValidationError(f"Could not download GitHub PR diff: {exc}") from exc
        if response.status_code != 200:
            raise ValidationError(
                f"Failed to fetch GitHub PR diff from {diff_url} (HTTP {response.status_code})"
            )
        diff_raw = response.text

    if not diff_raw:
        raise ValidationError(
            "No git diff provided. Please paste a unified diff or provide a valid GitHub PR URL."
        )

    requirements: list[dict[str, Any]] = []
    if not spec_raw:
        rows = db.execute(
            select(Requirement)
            .where(
                Requirement.project_id == project_id,
                Requirement.user_id == user_id,
                Requirement.state != RequirementState.REJECTED,
            )
            .order_by(Requirement.created_at.asc())
        ).scalars().all()
        requirements = [
            {"id": f"R{index}", "title": row.title, "description": row.description or row.title}
            for index, row in enumerate(rows, start=1)
        ]
        if not requirements:
            raise ValidationError(
                "No requirements found. Please provide a spec text or upload a project document."
            )

    return run_pr_verification_workflow(
        project_id=project_id,
        user_id=user_id,
        spec_text=spec_raw,
        raw_diff=diff_raw,
        pr_url=pr_url or None,
        requirements=requirements if not spec_raw else None,
        db=db,
    )


def _ensure_requirement_revision(
    db: Session, *, project_id: str, user_id: str, title: str, description: str
) -> RequirementRevision:
    """Pin the exact requirement text a run verified (reused across identical re-runs)."""
    requirement = db.execute(
        select(Requirement).where(
            Requirement.project_id == project_id,
            Requirement.title == title,
        )
    ).scalars().first()
    if requirement is None:
        requirement = Requirement(
            project_id=project_id,
            user_id=user_id,
            title=title,
            description=description or None,
        )
        db.add(requirement)
        db.flush()

    content_hash = hashlib.sha256(f"{title}\n{description}".encode()).hexdigest()
    revision = db.execute(
        select(RequirementRevision).where(
            RequirementRevision.requirement_id == requirement.id,
            RequirementRevision.content_hash == content_hash,
        )
    ).scalar_one_or_none()
    if revision is None:
        max_revision = db.execute(
            select(func.max(RequirementRevision.revision)).where(
                RequirementRevision.requirement_id == requirement.id
            )
        ).scalar_one() or 0
        revision = RequirementRevision(
            requirement_id=requirement.id,
            project_id=project_id,
            user_id=user_id,
            revision=max_revision + 1,
            title=title,
            description=description or None,
            acceptance_criteria=[],
            content_hash=content_hash,
        )
        db.add(revision)
        db.flush()
    return revision


def _ensure_evidence_file(
    db: Session, *, snapshot_id: str, project_id: str, path: str, snippet: str
) -> RepositoryFile:
    """Resolve a diff-only evidence path to a file row so the FK stays valid."""
    record = db.execute(
        select(RepositoryFile).where(
            RepositoryFile.snapshot_id == snapshot_id,
            RepositoryFile.path == path,
        )
    ).scalar_one_or_none()
    if record is not None:
        return record
    snippet_hash = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
    record = RepositoryFile(
        snapshot_id=snapshot_id,
        project_id=project_id,
        path=path,
        blob_sha=snippet_hash,
        content_hash=snippet_hash,
        language=None,
        size_bytes=len(snippet.encode("utf-8")),
        line_count=None,
        is_binary=False,
    )
    db.add(record)
    db.flush()
    return record


def persist_verification_run(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    brief: PRTrustBrief,
    requirements: list[dict[str, Any]],
    diff_hash: str,
    pr_url: str | None,
) -> str | None:
    """Best-effort audit-trail write. Returns the run id, or None on failure.

    Never raises: a failed audit-trail write must not fail verification.
    """
    try:
        from app.api.services.repo_index_service import get_or_create_snapshot

        snapshot = get_or_create_snapshot(
            db,
            project_id=project_id,
            user_id=user_id,
            commit_sha=f"pr-{diff_hash}",
            ref_name=pr_url,
            kind=SnapshotKind.PULL_REQUEST,
        )
        run = VerificationRun(
            snapshot_id=snapshot.id,
            project_id=project_id,
            user_id=user_id,
            status=RunStatus.SUCCEEDED,
            verifier_version=VERIFIER_VERSION,
            model_name=get_settings().llm_model,
            started_at=datetime.now(UTC).replace(tzinfo=None),
            completed_at=datetime.now(UTC).replace(tzinfo=None),
            metadata_json={
                "brief": brief.model_dump(),
                "diffHash": diff_hash,
                "prUrl": pr_url,
                "providerId": getattr(get_ai_provider(), "id", None),
            },
        )
        db.add(run)
        db.flush()

        descriptions = {str(r.get("id")): str(r.get("description", "")) for r in requirements}
        for verdict in brief.verdicts:
            revision = _ensure_requirement_revision(
                db,
                project_id=project_id,
                user_id=user_id,
                title=verdict.title,
                description=descriptions.get(verdict.reqId, verdict.rationale),
            )
            record = RequirementVerdict(
                verification_run_id=run.id,
                requirement_revision_id=revision.id,
                project_id=project_id,
                verdict=_STATUS_TO_VERDICT.get(verdict.status, VerificationVerdict.INCONCLUSIVE),
                confidence=_CONFIDENCE_TO_SCORE.get(verdict.confidence, 0.6),
                rationale=verdict.rationale,
            )
            db.add(record)
            db.flush()

            if verdict.evidenceFile and verdict.evidenceSnippet:
                quote = verdict.evidenceSnippet[:2000]
                file_record = _ensure_evidence_file(
                    db,
                    snapshot_id=snapshot.id,
                    project_id=project_id,
                    path=verdict.evidenceFile,
                    snippet=quote,
                )
                db.add(EvidenceReference(
                    verdict_id=record.id,
                    project_id=project_id,
                    snapshot_id=snapshot.id,
                    file_id=file_record.id,
                    chunk_id=None,
                    kind=(
                        EvidenceKind.SUPPORTING
                        if verdict.status in ("covered", "partial")
                        else EvidenceKind.CONTEXT
                    ),
                    start_line=1,
                    end_line=max(1, quote.count("\n") + 1),
                    quote=quote,
                    quote_hash=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                    file_content_hash=file_record.content_hash,
                    relevance_score=_CONFIDENCE_TO_SCORE.get(verdict.confidence, 0.6),
                ))
        db.commit()
        return run.id
    except Exception as exc:  # noqa: BLE001
        logger.warning("Persisting verification run failed, continuing without audit trail: %s", exc)
        try:
            db.rollback()
        except Exception as rollback_exc:  # noqa: BLE001
            logger.debug("Audit-trail rollback failed: %s", rollback_exc)
        return None


def list_verification_runs(
    db: Session, *, project_id: str, user_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Newest-first run summaries for the Previous Runs tab (ownership-checked)."""
    get_owned_project(db, user_id, project_id)
    runs = db.execute(
        select(VerificationRun)
        .where(VerificationRun.project_id == project_id)
        .order_by(VerificationRun.created_at.desc())
        .limit(limit)
    ).scalars().all()
    summaries: list[dict[str, Any]] = []
    for run in runs:
        meta = run.metadata_json or {}
        brief_data = meta.get("brief") or {}
        verdict_counts = db.execute(
            select(RequirementVerdict.verdict, func.count())
            .where(RequirementVerdict.verification_run_id == run.id)
            .group_by(RequirementVerdict.verdict)
        ).all()
        counts = {v.value if hasattr(v, "value") else str(v): c for v, c in verdict_counts}
        summaries.append({
            "id": run.id,
            "title": brief_data.get("title") or f"Verification {run.id[:8]}",
            "commitSha": (run.snapshot.commit_sha[:8] if run.snapshot else ""),
            "coverageScore": brief_data.get("coverageScore", 0),
            "trustLevel": brief_data.get("trustLevel", "medium"),
            "totalRequirements": len(brief_data.get("verdicts", [])),
            "coveredCount": counts.get("satisfied", 0),
            "missingCount": counts.get("not_satisfied", 0),
            "createdAt": run.created_at.isoformat() if run.created_at else "",
        })
    return summaries


def get_verification_brief(
    db: Session, *, project_id: str, user_id: str, run_id: str
) -> PRTrustBrief | None:
    """Full brief for a persisted run, or None when missing/foreign."""
    get_owned_project(db, user_id, project_id)
    run = db.execute(
        select(VerificationRun).where(
            VerificationRun.id == run_id,
            VerificationRun.project_id == project_id,
        )
    ).scalar_one_or_none()
    if run is None:
        return None
    brief_data = (run.metadata_json or {}).get("brief")
    if not brief_data:
        return None
    try:
        return PRTrustBrief(**brief_data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Stored brief for run %s is unreadable: %s", run_id, exc)
        return None
