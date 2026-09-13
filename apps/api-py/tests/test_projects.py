"""Projects API tests - shared fixtures live in tests/conftest.py."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Source
from tests.conftest import (
    OTHER_USER_ID,
    PROJECT_KEYS,
    SOURCE_KEYS,
    seed_project,
    seed_source,
)

# ---- list ----


def test_list_projects_returns_empty_list(client: TestClient) -> None:
    response = client.get("/projects")

    assert response.status_code == 200
    assert response.json() == {"projects": []}


def test_list_projects_is_newest_first_with_source_counts(
    client: TestClient, db_session: Session
) -> None:
    older = seed_project(db_session, name="Older", created_at=datetime(2026, 7, 10, 9, 0, 0, tzinfo=UTC))
    newer = seed_project(db_session, name="Newer", created_at=datetime(2026, 7, 12, 9, 0, 0, tzinfo=UTC))
    seed_source(db_session, older, chunks=2)

    projects = client.get("/projects").json()["projects"]

    assert [p["id"] for p in projects] == [newer.id, older.id]
    assert set(projects[0]) == PROJECT_KEYS
    assert projects[0]["sourceCount"] == 0
    assert projects[1]["sourceCount"] == 1


def test_list_projects_excludes_other_users_projects(
    client: TestClient, db_session: Session
) -> None:
    seed_project(db_session, name="Not mine", user_id=OTHER_USER_ID)

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
    # ISO 8601 with millisecond precision, exactly like Date.toISOString().
    datetime.fromisoformat(project["createdAt"])


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
    project = seed_project(db_session, name="Apollo", description="Launch plan")
    source = seed_source(db_session, project, filename="spec.pdf", chunks=3)

    response = client.get(f"/projects/{project.id}")

    assert response.status_code == 200
    detail = response.json()["project"]
    assert set(detail) == PROJECT_KEYS | {"sources"}
    assert detail["sourceCount"] == 1

    source_dto = detail["sources"][0]
    assert set(source_dto) == SOURCE_KEYS
    assert source_dto["id"] == source.id
    assert source_dto["projectId"] == project.id
    assert source_dto["kind"] == "pdf"
    assert source_dto["status"] == "processed"
    assert source_dto["errorMessage"] is None
    assert source_dto["chunkCount"] == 3


def test_get_project_sources_are_newest_first(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    base = datetime(2026, 7, 16, 11, 0, 0, tzinfo=UTC)
    seed_source(db_session, project, filename="old.pdf", created_at=base)
    seed_source(db_session, project, filename="new.pdf", created_at=base + timedelta(hours=1))

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
    project = seed_project(db_session, user_id=OTHER_USER_ID)

    assert client.get(f"/projects/{project.id}").status_code == 404


# ---- update ----


def test_update_project_changes_only_provided_fields(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, name="Apollo", description="Launch plan")

    response = client.patch(f"/projects/{project.id}", json={"name": "Apollo II"})

    assert response.status_code == 200
    updated = response.json()["project"]
    assert set(updated) == PROJECT_KEYS
    assert updated["name"] == "Apollo II"
    assert updated["description"] == "Launch plan"


def test_update_project_can_clear_description(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session, name="Apollo", description="Launch plan")

    updated = client.patch(f"/projects/{project.id}", json={"description": None}).json()["project"]

    assert updated["description"] is None
    assert updated["name"] == "Apollo"


def test_update_project_keeps_source_count(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    seed_source(db_session, project, chunks=1)

    updated = client.patch(f"/projects/{project.id}", json={"name": "Renamed"}).json()["project"]

    assert updated["sourceCount"] == 1


def test_update_project_returns_404_when_missing(client: TestClient) -> None:
    assert client.patch("/projects/does-not-exist", json={"name": "Nope"}).status_code == 404


def test_update_project_owned_by_another_user_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, user_id=OTHER_USER_ID)

    assert client.patch(f"/projects/{project.id}", json={"name": "Nope"}).status_code == 404


# ---- delete ----


def test_delete_project_returns_204_and_removes_it(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)

    response = client.delete(f"/projects/{project.id}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/projects/{project.id}").status_code == 404
    assert client.get("/projects").json() == {"projects": []}


def test_delete_project_cascades_to_sources(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    seed_source(db_session, project, chunks=2)

    assert client.delete(f"/projects/{project.id}").status_code == 204
    assert db_session.query(Source).count() == 0


def test_delete_project_returns_404_when_missing(client: TestClient) -> None:
    assert client.delete("/projects/does-not-exist").status_code == 404


def test_delete_project_owned_by_another_user_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, user_id=OTHER_USER_ID)

    assert client.delete(f"/projects/{project.id}").status_code == 404


def test_delete_project_cleans_storage_and_qdrant(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    import app.providers.qdrant_provider as qdrant_module
    import app.providers.storage_provider as storage_module

    project = seed_project(db_session)
    seed_source(db_session, project, chunks=2)

    removed_prefixes: list[str] = []
    deleted_projects: list[str] = []

    class FakeStorage:
        def remove_prefix(self, prefix: str) -> None:
            removed_prefixes.append(prefix)

    class FakeIndex:
        def delete_by_project(self, project_id: str) -> None:
            deleted_projects.append(project_id)

    monkeypatch.setattr(storage_module, "get_storage", lambda: FakeStorage())
    monkeypatch.setattr(qdrant_module, "get_code_index", lambda: FakeIndex())

    assert client.delete(f"/projects/{project.id}").status_code == 204

    assert removed_prefixes == [f"projects/{project.id}/"]
    assert deleted_projects == [project.id]
    assert db_session.query(Source).count() == 0


def test_delete_project_still_204_when_cleanup_fails(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    import app.providers.qdrant_provider as qdrant_module
    import app.providers.storage_provider as storage_module

    project = seed_project(db_session)

    class BrokenStorage:
        def remove_prefix(self, prefix: str) -> None:
            raise RuntimeError("disk on fire")

    monkeypatch.setattr(storage_module, "get_storage", lambda: BrokenStorage())
    monkeypatch.setattr(qdrant_module, "get_code_index", lambda: None)

    assert client.delete(f"/projects/{project.id}").status_code == 204
    assert client.get(f"/projects/{project.id}").status_code == 404
