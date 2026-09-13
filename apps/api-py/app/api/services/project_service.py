"""Projects module - service layer (all DB access lives here).

Port of ``apps/api/src/modules/projects/service.ts``. Every query is filtered
by ``user_id``; a project that does not exist *or* is not owned by the caller
raises :class:`~app.core.errors.NotFoundError`, so the API never reveals the
existence of another user's rows.
"""
from __future__ import annotations

import logging

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

logger = logging.getLogger(__name__)

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
    """Hard-delete a project and everything it owns, everywhere.

    Postgres rows go via ORM + FK cascades. Blob storage
    (``projects/<id>/``) and Qdrant code points are removed best-effort
    afterwards: cleanup failures are logged but never fail the delete,
    so the API still returns 204 with no orphaned project row.
    """
    project = get_owned_project(db, user_id, project_id)
    db.delete(project)
    db.commit()

    try:
        from app.providers.storage_provider import get_storage

        get_storage().remove_prefix(f"projects/{project_id}/")
    except Exception:
        logger.warning("project storage cleanup failed (project_id=%s)", project_id, exc_info=True)

    try:
        from app.providers.qdrant_provider import get_code_index

        index = get_code_index()
        if index is not None:
            index.delete_by_project(project_id)
    except Exception:
        logger.warning("project qdrant cleanup failed (project_id=%s)", project_id, exc_info=True)

    try:
        from app.workers.arq_worker import _job_status_registry

        for job_id in [k for k in _job_status_registry if project_id in k]:
            _job_status_registry.pop(job_id, None)
    except Exception:
        logger.warning("project job-registry cleanup failed (project_id=%s)", project_id, exc_info=True)
