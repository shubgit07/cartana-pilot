"""Requirement routes — thin: validate, call service, return DTOs.

Port of ``apps/api/src/modules/requirements/router.ts``. Mounted at
``/projects/{project_id}/requirements``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.requirement import (
    RequirementDetailResponse,
    RequirementListResponse,
    RequirementResponse,
    UpdateRequirement,
)
from app.api.services import requirement_service
from app.db.session import get_db

router = APIRouter(tags=["requirements"])


@router.get("", response_model=RequirementListResponse)
def list_requirements(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> RequirementListResponse:
    return RequirementListResponse(
        requirements=requirement_service.list_requirements(db, user.id, project_id)
    )


@router.get("/{req_id}", response_model=RequirementDetailResponse)
def get_requirement(
    project_id: str,
    req_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> RequirementDetailResponse:
    return RequirementDetailResponse(
        requirement=requirement_service.get_requirement(db, user.id, project_id, req_id)
    )


@router.patch("/{req_id}", response_model=RequirementResponse)
def update_requirement(
    project_id: str,
    req_id: str,
    payload: UpdateRequirement,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> RequirementResponse:
    return RequirementResponse(
        requirement=requirement_service.update_requirement(db, user.id, project_id, req_id, payload)
    )


@router.delete("/{req_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_requirement(
    project_id: str,
    req_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    requirement_service.delete_requirement(db, user.id, project_id, req_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
