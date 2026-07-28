"""Projects module - service layer (all DB access lives here).

Port of ``apps/api/src/modules/projects/service.ts``. Every query is filtered
by ``user_id``; a project that does not exist *or* is not owned by the caller
raises :class:`~app.core.errors.NotFoundError`, so the API never reveals the
existence of another user's rows.
"""
from __future__ import annotations

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


def get_owned_project(db: Session, user_id: str, project_id: str) -> Project:
    """Load a project owned by ``user_id`` or raise ``NotFoundError``.

    Shared with the modules that hang off a project (sources, chat, ...) so
    ownership is enforced identically everywhere.
    """
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
    return [ProjectSummary.from_model(project, source_count) for project, source_count in rows]


def get_project(db: Session, user_id: str, project_id: str) -> ProjectDetail:
    project = get_owned_project(db, user_id, project_id)
    rows = db.execute(
        select(Source, _CHUNK_COUNT.label("chunk_count"))
        .where(Source.project_id == project.id)
        .order_by(Source.created_at.desc())
    ).all()
    sources = [SourceSummary.from_model(source, chunk_count) for source, chunk_count in rows]
    return ProjectDetail.from_project(project, sources)


def create_project(db: Session, user_id: str, payload: CreateProject) -> ProjectSummary:
    project = Project(user_id=user_id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectSummary.from_model(project, source_count=0)


def update_project(db: Session, user_id: str, project_id: str, payload: UpdateProject) -> ProjectSummary:
    project = get_owned_project(db, user_id, project_id)

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        project.name = changes["name"]
    if "description" in changes:
        project.description = changes["description"]

    db.commit()
    db.refresh(project)
    return ProjectSummary.from_model(project, _count_sources(db, project.id))


def delete_project(db: Session, user_id: str, project_id: str) -> None:
    project = get_owned_project(db, user_id, project_id)
    db.delete(project)
    db.commit()
