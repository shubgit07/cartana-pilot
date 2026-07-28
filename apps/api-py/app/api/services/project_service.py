"""Projects module - service layer (all DB access lives here).

Port of ``apps/api/src/modules/projects/service.ts``. Every query is filtered
by ``user_id``; a project that does not exist *or* is not owned by the caller
raises :class:`~app.core.errors.NotFoundError`, so the API never reveals the
existence of another user's rows.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.project import (
    CreateProject,
    ProjectDetail,
    ProjectSummary,
    SourceSummary,
    UpdateProject,
)
from app.core.errors import NotFoundError
from app.db.models import Chunk, Project, Source

# Correlated subqueries reproduce Prisma's ``_count`` selections without
# loading the related rows.
_SOURCE_COUNT = (
    select(func.count(Source.id)).where(Source.project_id == Project.id).correlate(Project).scalar_subquery()
)
_CHUNK_COUNT = (
    select(func.count(Chunk.id)).where(Chunk.source_id == Source.id).correlate(Source).scalar_subquery()
)


def to_iso8601(value: datetime) -> str:
    """Render a timestamp exactly like JavaScript's ``Date.toISOString()``.

    Timestamps are stored as naive UTC values (Prisma ``timestamp(3)``), so a
    naive value is treated as UTC and formatted with millisecond precision and
    a trailing ``Z``. The frontend parses these strings directly.
    """
    moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S')}.{moment.microsecond // 1000:03d}Z"


def _enum_value(value: object) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _to_summary(project: Project, source_count: int) -> ProjectSummary:
    return ProjectSummary(
        id=project.id,
        name=project.name,
        description=project.description,
        createdAt=to_iso8601(project.created_at),
        sourceCount=source_count,
    )


def _to_source_summary(source: Source, chunk_count: int) -> SourceSummary:
    return SourceSummary(
        id=source.id,
        projectId=source.project_id,
        filename=source.filename,
        kind=_enum_value(source.kind),
        status=_enum_value(source.status),
        errorMessage=source.error_message,
        createdAt=to_iso8601(source.created_at),
        chunkCount=chunk_count,
    )


def _get_owned_project(db: Session, user_id: str, project_id: str) -> Project:
    project = db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError("Project not found")
    return project


def _count_sources(db: Session, project_id: str) -> int:
    return int(
        db.execute(select(func.count(Source.id)).where(Source.project_id == project_id)).scalar_one()
    )


def list_projects(db: Session, user_id: str) -> list[ProjectSummary]:
    rows = db.execute(
        select(Project, _SOURCE_COUNT.label("source_count"))
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
    ).all()
    return [_to_summary(project, source_count) for project, source_count in rows]


def get_project(db: Session, user_id: str, project_id: str) -> ProjectDetail:
    project = _get_owned_project(db, user_id, project_id)
    rows = db.execute(
        select(Source, _CHUNK_COUNT.label("chunk_count"))
        .where(Source.project_id == project.id)
        .order_by(Source.created_at.desc())
    ).all()
    sources = [_to_source_summary(source, chunk_count) for source, chunk_count in rows]
    summary = _to_summary(project, len(sources))
    return ProjectDetail(**summary.model_dump(), sources=sources)


def create_project(db: Session, user_id: str, payload: CreateProject) -> ProjectSummary:
    project = Project(user_id=user_id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_summary(project, 0)


def update_project(db: Session, user_id: str, project_id: str, payload: UpdateProject) -> ProjectSummary:
    project = _get_owned_project(db, user_id, project_id)

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        project.name = changes["name"]
    if "description" in changes:
        project.description = changes["description"]

    db.commit()
    db.refresh(project)
    return _to_summary(project, _count_sources(db, project.id))


def delete_project(db: Session, user_id: str, project_id: str) -> None:
    project = _get_owned_project(db, user_id, project_id)
    db.delete(project)
    db.commit()
