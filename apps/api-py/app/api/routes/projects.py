"""Project routes - thin: resolve the caller, call the service, return DTOs.

Port of ``apps/api/src/modules/projects/router.ts``. The router is mounted at
``/projects`` in :mod:`app.api.router`, so the paths below match the Node
backend one-for-one.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.project import (
    CreateProject,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    UpdateProject,
)
from app.api.services import project_service
from app.db.session import get_db

router = APIRouter(tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ProjectListResponse:
    return ProjectListResponse(projects=project_service.list_projects(db, user.id))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreateProject,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ProjectResponse:
    return ProjectResponse(project=project_service.create_project(db, user.id, payload))


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ProjectDetailResponse:
    return ProjectDetailResponse(project=project_service.get_project(db, user.id, project_id))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: UpdateProject,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ProjectResponse:
    return ProjectResponse(project=project_service.update_project(db, user.id, project_id, payload))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    project_service.delete_project(db, user.id, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
