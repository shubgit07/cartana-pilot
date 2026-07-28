"""Tasks module — service layer.

Port of ``apps/api/src/modules/tasks/service.ts``. All queries filtered by
``user_id`` + ``project_id``. Manual task creation sets origin=user, state=accepted.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.requirement import ChunkLink, SourceLink
from app.api.schemas.task import (
    CreateTask,
    TaskDetail,
    TaskSummary,
    UpdateTask,
)
from app.api.services.project_service import get_owned_project
from app.core.errors import NotFoundError
from app.db.models import Chunk, Requirement, Source, Task, TaskChunk


def _load_chunk_links(db: Session, task_ids: list[str]) -> dict[str, list[ChunkLink]]:
    if not task_ids:
        return {}
    links = (
        db.execute(
            select(TaskChunk, Chunk, Source)
            .join(Chunk, Chunk.id == TaskChunk.chunk_id)
            .join(Source, Source.id == Chunk.source_id)
            .where(TaskChunk.task_id.in_(task_ids))
        )
        .all()
    )
    result: dict[str, list[ChunkLink]] = {}
    for tc, chunk, source in links:
        snippet = chunk.text[:240] + "\u2026" if len(chunk.text) > 240 else chunk.text
        result.setdefault(tc.task_id, []).append(
            ChunkLink(chunkId=chunk.id, sourceId=source.id, filename=source.filename, snippet=snippet)
        )
    return result


def _load_source_links(db: Session, task_ids: list[str]) -> dict[str, list[SourceLink]]:
    if not task_ids:
        return {}
    links = (
        db.execute(
            select(TaskChunk, Source)
            .join(Chunk, Chunk.id == TaskChunk.chunk_id)
            .join(Source, Source.id == Chunk.source_id)
            .where(TaskChunk.task_id.in_(task_ids))
        )
        .all()
    )
    result: dict[str, list[SourceLink]] = {}
    seen_sources: dict[str, set[str]] = {}
    for tc, source in links:
        seen = seen_sources.setdefault(tc.task_id, set())
        if source.id not in seen:
            seen.add(source.id)
            result.setdefault(tc.task_id, []).append(
                SourceLink(sourceId=source.id, filename=source.filename)
            )
    return result


def list_tasks(db: Session, user_id: str, project_id: str) -> list[TaskSummary]:
    get_owned_project(db, user_id, project_id)

    rows = db.execute(
        select(Task)
        .where(Task.project_id == project_id, Task.user_id == user_id)
        .order_by(Task.state.asc(), Task.created_at.desc())
    ).scalars().all()
    if not rows:
        return []

    source_links = _load_source_links(db, [t.id for t in rows])
    return [TaskSummary.from_model(t, source_links.get(t.id, [])) for t in rows]


def get_task(db: Session, user_id: str, project_id: str, task_id: str) -> TaskDetail:
    row = db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.project_id == project_id,
            Task.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Task not found")

    chunk_links = _load_chunk_links(db, [row.id])
    source_links = _load_source_links(db, [row.id])
    summary = TaskSummary.from_model(row, source_links.get(row.id, []))
    return TaskDetail(**summary.model_dump(), chunkLinks=chunk_links.get(row.id, []))


def create_task(
    db: Session, user_id: str, project_id: str, payload: CreateTask
) -> TaskSummary:
    get_owned_project(db, user_id, project_id)

    if payload.requirementId:
        req = db.execute(
            select(Requirement).where(
                Requirement.id == payload.requirementId,
                Requirement.project_id == project_id,
                Requirement.user_id == user_id,
            )
        ).scalar_one_or_none()
        if req is None:
            raise NotFoundError("Linked requirement not found in this project")

    task = Task(
        project_id=project_id,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        requirement_id=payload.requirementId,
        origin="user",
        state="accepted",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskSummary.from_model(task, [])


def update_task(
    db: Session,
    user_id: str,
    project_id: str,
    task_id: str,
    payload: UpdateTask,
) -> TaskSummary:
    row = db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.project_id == project_id,
            Task.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Task not found")

    changes = payload.model_dump(exclude_unset=True)

    if changes.get("requirementId"):
        req = db.execute(
            select(Requirement).where(
                Requirement.id == changes["requirementId"],
                Requirement.project_id == project_id,
                Requirement.user_id == user_id,
            )
        ).scalar_one_or_none()
        if req is None:
            raise NotFoundError("Linked requirement not found in this project")

    touched = bool(changes)
    next_state = changes.get("state", row.state.value)
    if touched and next_state == "suggested" and row.origin.value == "ai":
        final_state = "edited"
    else:
        final_state = next_state

    if "title" in changes:
        row.title = changes["title"]
    if "description" in changes:
        row.description = changes["description"]
    if "requirementId" in changes:
        row.requirement_id = changes["requirementId"]
    row.state = final_state
    if row.origin.value == "ai" and touched:
        row.origin = "user"

    db.commit()
    db.refresh(row)
    source_links = _load_source_links(db, [row.id])
    return TaskSummary.from_model(row, source_links.get(row.id, []))


def delete_task(db: Session, user_id: str, project_id: str, task_id: str) -> None:
    row = db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.project_id == project_id,
            Task.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Task not found")
    db.delete(row)
    db.commit()
