"""Task routes — CRUD + state transitions + relink.

Port of ``apps/api/src/modules/tasks/router.ts``. Mounted at
``/projects/{project_id}/tasks``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.task import (
    CreateTask,
    TaskDetailResponse,
    TaskListResponse,
    TaskResponse,
    UpdateTask,
)
from app.api.services import task_service
from app.db.session import get_db

router = APIRouter(tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaskListResponse:
    return TaskListResponse(tasks=task_service.list_tasks(db, user.id, project_id))


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: str,
    payload: CreateTask,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    return TaskResponse(task=task_service.create_task(db, user.id, project_id, payload))


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaskDetailResponse:
    return TaskDetailResponse(task=task_service.get_task(db, user.id, project_id, task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    project_id: str,
    task_id: str,
    payload: UpdateTask,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    return TaskResponse(
        task=task_service.update_task(db, user.id, project_id, task_id, payload)
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    task_service.delete_task(db, user.id, project_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
