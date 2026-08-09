"""Sources API tests.

Storage is redirected to a temporary directory and the ARQ enqueue call is
replaced with a recorder, so the suite needs neither Redis nor a real storage
root. Shared fixtures live in tests/conftest.py.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.services import source_service
from app.db.models import Source, SourceKind, SourceStatus
from app.providers.storage_provider import LocalStorageProvider
from tests.conftest import (
    JOB_STATUS_KEYS,
    OTHER_USER_ID,
    SOURCE_KEYS,
    seed_project,
    seed_source,
)


@pytest.fixture(autouse=True)
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LocalStorageProvider:
    provider = LocalStorageProvider(tmp_path)
    monkeypatch.setattr(source_service, "get_storage", lambda: provider)
    return provider


@pytest.fixture(autouse=True)
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(source_service, "enqueue_ingest", lambda **kwargs: calls.append(kwargs))
    return calls


def _stored_key(db: Session, source_id: str) -> str:
    source = db.get(Source, source_id)
    assert source is not None
    return source.storage_key


# ---- list ----


def test_list_sources_returns_empty_list(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)

    response = client.get(f"/projects/{project.id}/sources")

    assert response.status_code == 200
    assert response.json() == {"sources": []}


def test_list_sources_is_newest_first_with_chunk_counts(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)
    base = datetime(2026, 7, 16, 11, 0, 0, tzinfo=UTC)
    seed_source(db_session, project, filename="old.pdf", created_at=base, chunks=1)
    seed_source(db_session, project, filename="new.pdf", created_at=base + timedelta(hours=1))

    sources = client.get(f"/projects/{project.id}/sources").json()["sources"]

    assert [s["filename"] for s in sources] == ["new.pdf", "old.pdf"]
    assert set(sources[0]) == SOURCE_KEYS
    assert sources[1]["chunkCount"] == 1


def test_list_sources_excludes_other_projects(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session, name="Mine")
    other_project = seed_project(db_session, name="Other")
    seed_source(db_session, other_project, filename="elsewhere.pdf")

    assert client.get(f"/projects/{project.id}/sources").json() == {"sources": []}


# ---- create from text ----


def test_create_source_from_text_returns_201_and_exact_shape(
    client: TestClient, db_session: Session, storage: LocalStorageProvider
) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources/text",
        json={"filename": "notes.md", "content": "# Requirements\nShip it."},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"source"}

    source = body["source"]
    assert set(source) == SOURCE_KEYS
    assert source["projectId"] == project.id
    assert source["filename"] == "notes.md"
    assert source["kind"] == "text"
    assert source["status"] == "uploaded"
    assert source["errorMessage"] is None
    assert source["chunkCount"] == 0
    datetime.fromisoformat(source["createdAt"])

    key = _stored_key(db_session, source["id"])
    assert key.startswith(f"projects/{project.id}/")
    assert "\\" not in key
    assert storage.path_for(key).read_bytes() == b"# Requirements\nShip it."


def test_create_source_from_text_enqueues_ingest(
    client: TestClient, db_session: Session, enqueued: list[dict[str, Any]]
) -> None:
    project = seed_project(db_session)

    source = client.post(
        f"/projects/{project.id}/sources/text",
        json={"filename": "notes.txt", "content": "hello"},
    ).json()["source"]

    assert enqueued == [{"source_id": source["id"], "project_id": project.id, "user_id": source["projectId"] and enqueued[0]["user_id"]}]


def test_create_source_from_text_requires_content(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources/text", json={"filename": "notes.txt", "content": ""}
    )

    assert response.status_code == 422


def test_create_source_in_unknown_project_returns_404(client: TestClient) -> None:
    response = client.post(
        "/projects/does-not-exist/sources/text",
        json={"filename": "notes.txt", "content": "hello"},
    )

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Project not found"}}


def test_create_source_in_another_users_project_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, user_id=OTHER_USER_ID)

    response = client.post(
        f"/projects/{project.id}/sources/text",
        json={"filename": "notes.txt", "content": "hello"},
    )

    assert response.status_code == 404


# ---- upload ----


def test_upload_text_file_creates_source(
    client: TestClient, db_session: Session, storage: LocalStorageProvider
) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 201
    source = response.json()["source"]
    assert set(source) == SOURCE_KEYS
    assert source["filename"] == "notes.txt"
    assert source["kind"] == "text"
    assert source["status"] == "uploaded"
    assert storage.path_for(_stored_key(db_session, source["id"])).read_bytes() == b"plain text"


def test_upload_pdf_infers_pdf_kind(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources",
        files={"file": ("spec.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["source"]["kind"] == "pdf"


def test_upload_sanitises_windows_style_filenames(
    client: TestClient, db_session: Session, storage: LocalStorageProvider
) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources",
        files={"file": ("my notes (final).txt", b"text", "text/plain")},
    )

    source = response.json()["source"]
    key = _stored_key(db_session, source["id"])

    assert source["filename"] == "my notes (final).txt"  # display name is preserved
    assert key.endswith("my_notes__final_.txt")
    assert storage.path_for(key).exists()


def test_upload_unsupported_file_type_returns_400(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources",
        files={"file": ("archive.zip", b"PK\x03\x04", "application/zip")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_upload_empty_file_returns_400(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)

    response = client.post(
        f"/projects/{project.id}/sources", files={"file": ("notes.txt", b"", "text/plain")}
    )

    assert response.status_code == 400


def test_upload_over_the_size_limit_returns_413(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)
    oversized = b"x" * (source_service.MAX_UPLOAD_BYTES + 1)

    response = client.post(
        f"/projects/{project.id}/sources",
        files={"file": ("notes.txt", oversized, "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert db_session.query(Source).count() == 0


def test_upload_without_file_field_returns_422(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)

    assert client.post(f"/projects/{project.id}/sources").status_code == 422


# ---- get ----


def test_get_source_returns_summary(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    source = seed_source(db_session, project, chunks=2)

    response = client.get(f"/projects/{project.id}/sources/{source.id}")

    assert response.status_code == 200
    dto = response.json()["source"]
    assert set(dto) == SOURCE_KEYS
    assert dto["id"] == source.id
    assert dto["chunkCount"] == 2


def test_get_source_from_the_wrong_project_returns_400(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, name="Mine")
    other_project = seed_project(db_session, name="Other")
    source = seed_source(db_session, other_project)

    response = client.get(f"/projects/{project.id}/sources/{source.id}")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Source does not belong to this project",
        }
    }


def test_get_unknown_source_returns_404(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)

    response = client.get(f"/projects/{project.id}/sources/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Source not found"}}


def test_get_source_owned_by_another_user_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, user_id=OTHER_USER_ID)
    source = seed_source(db_session, project)

    assert client.get(f"/projects/{project.id}/sources/{source.id}").status_code == 404


# ---- job status ----


def test_job_status_reports_chunk_progress(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    source = seed_source(
        db_session,
        project,
        status=SourceStatus.PROCESSING,
        kind=SourceKind.TEXT,
        chunks=4,
        embedded=3,
    )

    response = client.get(f"/projects/{project.id}/sources/{source.id}/status")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status"}

    status = body["status"]
    assert set(status) == JOB_STATUS_KEYS
    assert status == {
        "sourceId": source.id,
        "status": "processing",
        "stage": "chunking",
        "chunksTotal": 4,
        "embedded": 3,
        "errorMessage": None,
    }


def test_job_status_stage_maps_processing_without_chunks_to_uploading(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)
    source = seed_source(db_session, project, status=SourceStatus.PROCESSING)

    status = client.get(f"/projects/{project.id}/sources/{source.id}/status").json()["status"]

    assert status["status"] == "processing"
    assert status["stage"] == "uploading"
    assert status["chunksTotal"] == 0


def test_job_status_stage_is_ready_for_processed(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    source = seed_source(db_session, project, status=SourceStatus.PROCESSED)

    status = client.get(f"/projects/{project.id}/sources/{source.id}/status").json()["status"]

    assert status["status"] == "processed"
    assert status["stage"] == "ready"


def test_job_status_reports_failures(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)
    source = seed_source(
        db_session, project, status=SourceStatus.FAILED, error_message="boom"
    )

    status = client.get(f"/projects/{project.id}/sources/{source.id}/status").json()["status"]

    assert status["status"] == "failed"
    assert status["errorMessage"] == "boom"
    assert status["chunksTotal"] == 0
    assert status["embedded"] == 0


def test_job_status_for_unknown_source_returns_404(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session)

    assert client.get(f"/projects/{project.id}/sources/nope/status").status_code == 404


# ---- delete ----


def test_delete_source_returns_204_and_removes_file(
    client: TestClient, db_session: Session, storage: LocalStorageProvider
) -> None:
    project = seed_project(db_session)
    created = client.post(
        f"/projects/{project.id}/sources/text",
        json={"filename": "notes.txt", "content": "hello"},
    ).json()["source"]
    key = _stored_key(db_session, created["id"])
    assert storage.path_for(key).exists()

    response = client.delete(f"/projects/{project.id}/sources/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert not storage.path_for(key).exists()
    assert client.get(f"/projects/{project.id}/sources").json() == {"sources": []}


def test_delete_unknown_source_returns_404(client: TestClient, db_session: Session) -> None:
    project = seed_project(db_session)

    assert client.delete(f"/projects/{project.id}/sources/nope").status_code == 404


def test_delete_source_from_the_wrong_project_returns_400(
    client: TestClient, db_session: Session
) -> None:
    project = seed_project(db_session, name="Mine")
    other_project = seed_project(db_session, name="Other")
    source = seed_source(db_session, other_project)

    assert client.delete(f"/projects/{project.id}/sources/{source.id}").status_code == 400
