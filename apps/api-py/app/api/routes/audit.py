"""Audit + Coverage routes.

Port of ``apps/api/src/modules/audit/router.ts``. Two routers:
- audit: mounted at ``/projects/{project_id}/audit``
- coverage: mounted at ``/projects/{project_id}/coverage``
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.audit import (
    AuditJobStatusResponse,
    AuditRunDetailResponse,
    AuditRunListResponse,
    AuditRunResponse,
    CoverageLinkListResponse,
    CoverageLinkResponse,
    PRTrustBriefResponse,
    UpdateCoverageLink,
    VerifyPRInput,
)
from app.api.services import audit_service
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.workers.tasks.ingest import enqueue_audit

audit_router = APIRouter(tags=["audit"])
coverage_router = APIRouter(tags=["coverage"])


# ---- Audit endpoints ----


@audit_router.post("/run", response_model=AuditRunResponse)
def trigger_audit(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AuditRunResponse:
    from app.api.services.project_service import get_owned_project
    get_owned_project(db, user.id, project_id)

    job_id = enqueue_audit(project_id, user.id)
    if job_id is None:
        raise NotFoundError("Could not queue audit job — broker may be unavailable")
    return AuditRunResponse(jobId=job_id, status="queued")


@audit_router.get("/runs", response_model=AuditRunListResponse)
def list_audit_runs(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AuditRunListResponse:
    return AuditRunListResponse(runs=audit_service.list_audit_runs(db, user.id, project_id))


@audit_router.get("/latest", response_model=AuditRunDetailResponse)
def get_latest_audit(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AuditRunDetailResponse:
    run = audit_service.get_latest_audit(db, user.id, project_id)
    if run is None:
        raise NotFoundError("No audit run found for this project")
    return AuditRunDetailResponse(run=run)


@audit_router.get("/run/{job_id}/status", response_model=AuditJobStatusResponse)
def get_audit_job_status(
    project_id: str,
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> AuditJobStatusResponse:
    from app.workers.arq_worker import get_job_status

    job_info = get_job_status(job_id)
    return AuditJobStatusResponse(
        jobId=job_id,
        state=job_info.get("state", "UNKNOWN"),
        result=job_info.get("result"),
    )


@audit_router.post("/verify-pr", response_model=PRTrustBriefResponse)
def verify_pr(
    project_id: str,
    payload: VerifyPRInput,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PRTrustBriefResponse:
    """Run decomposed PR Trust Brief verification on diff and spec."""
    brief, from_cache = audit_service.verify_pr_and_generate_trust_brief(
        db=db,
        user_id=user.id,
        project_id=project_id,
        input_data=payload,
    )
    return PRTrustBriefResponse(brief=brief, fromCache=from_cache)


# ---- Coverage endpoints ----


@coverage_router.get("", response_model=CoverageLinkListResponse)
def list_coverage_links(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CoverageLinkListResponse:
    return CoverageLinkListResponse(
        coverageLinks=audit_service.list_coverage_links(db, user.id, project_id)
    )


@coverage_router.patch("/{link_id}", response_model=CoverageLinkResponse)
def update_coverage_link(
    project_id: str,
    link_id: str,
    payload: UpdateCoverageLink,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CoverageLinkResponse:
    return CoverageLinkResponse(
        coverageLink=audit_service.update_coverage_link(
            db, user.id, project_id, link_id, payload
        )
    )
