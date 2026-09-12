"""PR Trust Brief verification route."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.audit import (
    PRTrustBrief,
    PRTrustBriefResponse,
    VerificationRunListResponse,
    VerificationRunSummary,
    VerifyPRInput,
)
from app.api.services import pr_trust_service
from app.db.session import get_db

router = APIRouter(tags=["audit"])


@router.post("/verify-pr", response_model=PRTrustBriefResponse)
def verify_pr(
    project_id: str,
    payload: VerifyPRInput,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PRTrustBriefResponse:
    """Verify a pasted diff or public PR against supplied or stored requirements."""
    brief, from_cache = pr_trust_service.verify_pr_and_generate_trust_brief(
        db=db,
        user_id=user.id,
        project_id=project_id,
        input_data=payload,
    )
    return PRTrustBriefResponse(brief=brief, fromCache=from_cache)


@router.get("/runs", response_model=VerificationRunListResponse)
def list_runs(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> VerificationRunListResponse:
    """Newest-first persisted verification runs for the Previous Runs tab."""
    runs = pr_trust_service.list_verification_runs(db, project_id=project_id, user_id=user.id)
    return VerificationRunListResponse(runs=[VerificationRunSummary(**r) for r in runs])


@router.get("/runs/{run_id}", response_model=PRTrustBrief)
def get_run(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PRTrustBrief:
    """Full persisted brief for a single run (powers View Report)."""
    brief = pr_trust_service.get_verification_brief(
        db, project_id=project_id, user_id=user.id, run_id=run_id
    )
    if brief is None:
        raise HTTPException(status_code=404, detail="Verification run not found")
    return brief
