"""Shared test plumbing.

Tests run against a throwaway in-memory SQLite database so no Postgres (and no
configuration) is required: ``get_db`` is overridden with a session bound to
that engine, and pgvector's column type is compiled to a plain BLOB for the
SQLite dialect only.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.models import Chunk, Project, Source, SourceKind, SourceStatus, User
from app.db.session import get_db
from app.main import app

# Exact JSON keys the frontend parses - no field may be added or renamed.
PROJECT_KEYS = {"id", "name", "description", "createdAt", "sourceCount"}
SOURCE_KEYS = {
    "id",
    "projectId",
    "filename",
    "kind",
    "status",
    "errorMessage",
    "createdAt",
    "chunkCount",
}
JOB_STATUS_KEYS = {"sourceId", "status", "chunksTotal", "embedded", "errorMessage"}

DEV_USER = get_current_user()
OTHER_USER_ID = "other-user"

EMBEDDING_DIM = Chunk.__table__.c.embedding.type.dim


@compiles(Vector, "sqlite")
def _compile_vector_for_sqlite(type_, compiler, **kw) -> str:  # pragma: no cover - schema shim
    return "BLOB"


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.add_all(
        [
            User(id=DEV_USER.id, email=DEV_USER.email, name=DEV_USER.name),
            User(id=OTHER_USER_ID, email="other@cartana.local", name="Other User"),
        ]
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed_project(
    db: Session,
    *,
    name: str = "Seeded project",
    description: Optional[str] = None,
    user_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Project:
    project = Project(
        user_id=user_id or DEV_USER.id,
        name=name,
        description=description,
        created_at=created_at or datetime(2026, 7, 16, 10, 30, 0),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def seed_source(
    db: Session,
    project: Project,
    *,
    filename: str = "spec.pdf",
    kind: SourceKind = SourceKind.PDF,
    status: SourceStatus = SourceStatus.PROCESSED,
    chunks: int = 0,
    embedded: int = 0,
    error_message: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Source:
    source = Source(
        project_id=project.id,
        user_id=project.user_id,
        filename=filename,
        kind=kind,
        status=status,
        storage_key=f"projects/{project.id}/1752660000000-{filename}",
        mime_type="application/pdf" if kind is SourceKind.PDF else "text/plain",
        size_bytes=2048,
        error_message=error_message,
        created_at=created_at or datetime(2026, 7, 16, 11, 0, 0),
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    for position in range(chunks):
        db.add(
            Chunk(
                source_id=source.id,
                position=position,
                text=f"chunk {position}",
                embedding=[0.0] * EMBEDDING_DIM if position < embedded else None,
            )
        )
    db.commit()
    return source
