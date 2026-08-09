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
    TaskGenerateResponse,
    TaskGenerateStatusResponse,
    TaskListResponse,
    TaskResponse,
    UpdateTask,
)
from app.api.services import task_service
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.workers.tasks.ingest import enqueue_task_generation

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


@router.post("/generate", response_model=TaskGenerateResponse)
def generate_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaskGenerateResponse:
    from app.api.services.project_service import get_owned_project
    get_owned_project(db, user.id, project_id)

    job_id = enqueue_task_generation(project_id, user.id)
    if job_id is None:
        raise NotFoundError("Could not queue task generation — broker may be unavailable")
    return TaskGenerateResponse(jobId=job_id, status="queued")


@router.get("/generate/{job_id}/status", response_model=TaskGenerateStatusResponse)
def get_task_generation_status(
    project_id: str,
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> TaskGenerateStatusResponse:
    from app.workers.arq_worker import get_job_status

    job_info = get_job_status(job_id)
    return TaskGenerateStatusResponse(
        jobId=job_id,
        state=job_info.get("state", "UNKNOWN"),
        result=job_info.get("result"),
    )


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
