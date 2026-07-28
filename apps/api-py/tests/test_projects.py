"""Projects API tests.

The suite runs against a throwaway in-memory SQLite database, so it needs no
Postgres instance: ``get_db`` is overridden with a session bound to that
engine and the pgvector column type is compiled to a plain BLOB for SQLite
only. Assertions pin the exact JSON the Next.js frontend parses.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta

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

DEV_USER = get_current_user()
OTHER_USER_ID = "other-user"


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


def _seed_project(
    db: Session,
    *,
    name: str = "Seeded project",
    description: str | None = None,
    user_id: str | None = None,
    created_at: datetime | None = None,
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


def _seed_source(
    db: Session,
    project: Project,
    *,
    filename: str = "spec.pdf",
    chunks: int = 0,
    created_at: datetime | None = None,
) -> Source:
    source = Source(
        project_id=project.id,
        user_id=project.user_id,
        filename=filename,
        kind=SourceKind.PDF,
        status=SourceStatus.PROCESSED,
        storage_key=f"local/{filename}",
        mime_type="application/pdf",
        size_bytes=2048,
        created_at=created_at or datetime(2026, 7, 16, 11, 0, 0),
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    for position in range(chunks):
        db.add(Chunk(source_id=source.id, position=position, text=f"chunk {position}"))
    db.commit()
    return source


# ---- list ----


def test_list_projects_returns_empty_list(client: TestClient) -> None:
    response = client.get("/projects")

    assert response.status_code == 200
    assert response.json() == {"projects": []}


def test_list_projects_is_newest_first_with_source_counts(
    client: TestClient, db_session: Session
) -> None:
    older = _seed_project(db_session, name="Older", created_at=datetime(2026, 7, 10, 9, 0, 0))
    newer = _seed_project(db_session, name="Newer", created_at=datetime(2026, 7, 12, 9, 0, 0))
    _seed_source(db_session, older, chunks=2)

    body = client.get("/projects").json()
    projects = body["projects"]

    assert [p["id"] for p in projects] == [newer.id, older.id]
    assert set(projects[0]) == PROJECT_KEYS
    assert projects[0]["sourceCount"] == 0
    assert projects[1]["sourceCount"] == 1


def test_list_projects_excludes_other_users_projects(
    client: TestClient, db_session: Session
) -> None:
    _seed_project(db_session, name="Not mine", user_id=OTHER_USER_ID)

    assert client.get("/projects").json() == {"projects": []}


# ---- create ----


def test_create_project_returns_201_and_exact_summary_shape(client: TestClient) -> None:
    response = client.post("/projects", json={"name": "Apollo", "description": "Launch plan"})

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"project"}

    project = body["project"]
    assert set(project) == PROJECT_KEYS
    assert project["name"] == "Apollo"
    assert project["description"] == "Launch plan"
    assert project["sourceCount"] == 0
    assert isinstance(project["createdAt"], str)
    assert project["createdAt"].endswith("Z")
    # ISO 8601 with millisecond precision, exactly like Date.toISOString().
    datetime.strptime(project["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ")


def test_create_project_defaults_description_to_null(client: TestClient) -> None:
    project = client.post("/projects", json={"name": "No description"}).json()["project"]

    assert project["description"] is None


def test_create_project_rejects_empty_name(client: TestClient) -> None:
    assert client.post("/projects", json={"name": ""}).status_code == 422


def test_created_project_appears_in_list(client: TestClient) -> None:
    created = client.post("/projects", json={"name": "Apollo"}).json()["project"]

    projects = client.get("/projects").json()["projects"]

    assert [p["id"] for p in projects] == [created["id"]]


# ---- get ----


def test_get_project_returns_detail_with_sources_and_chunk_counts(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session, name="Apollo", description="Launch plan")
    source = _seed_source(db_session, project, filename="spec.pdf", chunks=3)

    response = client.get(f"/projects/{project.id}")

    assert response.status_code == 200
    detail = response.json()["project"]
    assert set(detail) == PROJECT_KEYS | {"sources"}
    assert detail["id"] == project.id
    assert detail["sourceCount"] == 1

    assert len(detail["sources"]) == 1
    source_dto = detail["sources"][0]
    assert set(source_dto) == SOURCE_KEYS
    assert source_dto["id"] == source.id
    assert source_dto["projectId"] == project.id
    assert source_dto["filename"] == "spec.pdf"
    assert source_dto["kind"] == "pdf"
    assert source_dto["status"] == "processed"
    assert source_dto["errorMessage"] is None
    assert source_dto["chunkCount"] == 3
    assert source_dto["createdAt"].endswith("Z")


def test_get_project_sources_are_newest_first(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    base = datetime(2026, 7, 16, 11, 0, 0)
    _seed_source(db_session, project, filename="old.pdf", created_at=base)
    _seed_source(db_session, project, filename="new.pdf", created_at=base + timedelta(hours=1))

    detail = client.get(f"/projects/{project.id}").json()["project"]

    assert [s["filename"] for s in detail["sources"]] == ["new.pdf", "old.pdf"]
    assert detail["sourceCount"] == 2


def test_get_project_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/projects/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Project not found"}}


def test_get_project_owned_by_another_user_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session, user_id=OTHER_USER_ID)

    assert client.get(f"/projects/{project.id}").status_code == 404


# ---- update ----


def test_update_project_changes_only_provided_fields(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session, name="Apollo", description="Launch plan")

    response = client.patch(f"/projects/{project.id}", json={"name": "Apollo II"})

    assert response.status_code == 200
    updated = response.json()["project"]
    assert set(updated) == PROJECT_KEYS
    assert updated["name"] == "Apollo II"
    assert updated["description"] == "Launch plan"


def test_update_project_can_clear_description(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session, name="Apollo", description="Launch plan")

    updated = client.patch(f"/projects/{project.id}", json={"description": None}).json()["project"]

    assert updated["description"] is None
    assert updated["name"] == "Apollo"


def test_update_project_keeps_source_count(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    _seed_source(db_session, project, chunks=1)

    updated = client.patch(f"/projects/{project.id}", json={"name": "Renamed"}).json()["project"]

    assert updated["sourceCount"] == 1


def test_update_project_returns_404_when_missing(client: TestClient) -> None:
    response = client.patch("/projects/does-not-exist", json={"name": "Nope"})

    assert response.status_code == 404


def test_update_project_owned_by_another_user_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session, user_id=OTHER_USER_ID)

    assert client.patch(f"/projects/{project.id}", json={"name": "Nope"}).status_code == 404


# ---- delete ----


def test_delete_project_returns_204_and_removes_it(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session)

    response = client.delete(f"/projects/{project.id}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/projects/{project.id}").status_code == 404
    assert client.get("/projects").json() == {"projects": []}


def test_delete_project_cascades_to_sources(client: TestClient, db_session: Session) -> None:
    project = _seed_project(db_session)
    _seed_source(db_session, project, chunks=2)

    assert client.delete(f"/projects/{project.id}").status_code == 204
    assert db_session.query(Source).count() == 0


def test_delete_project_returns_404_when_missing(client: TestClient) -> None:
    assert client.delete("/projects/does-not-exist").status_code == 404


def test_delete_project_owned_by_another_user_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = _seed_project(db_session, user_id=OTHER_USER_ID)

    assert client.delete(f"/projects/{project.id}").status_code == 404
