"""Tests for the Qdrant-first code index (vector mirror + retrieval).

Qdrant is faked at the service seam: no cluster is required. Postgres stays
the source of truth; Qdrant holds ``{id, vector, payload}`` mirrors.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.api.services.repo_index_service import (
    IndexFileInput,
    retrieve_code_context,
    sync_repository_snapshot,
)
from app.db.models import CodeChunk
from app.providers.qdrant_provider import CodePoint, QdrantHit, build_code_points
from tests.conftest import seed_project


class FakeCodeIndex:
    """In-memory stand-in for QdrantCodeIndex (same method shapes)."""

    def __init__(self, hits: list[QdrantHit] | None = None) -> None:
        self.hits = hits or []
        self.ensure_called = False
        self.upserted: list[CodePoint] = []

    def ensure_collection(self) -> None:
        self.ensure_called = True

    def upsert_chunks(self, points: list[CodePoint]) -> int:
        self.upserted.extend(points)
        return len(points)

    def search(self, *, project_id: str, vector: list[float], top_k: int = 3) -> list[QdrantHit]:
        assert project_id and vector
        return self.hits[:top_k]


def _patch_index(monkeypatch, fake: FakeCodeIndex | None):
    monkeypatch.setattr(
        "app.api.services.repo_index_service.get_code_index", lambda: fake
    )


def test_sync_mirrors_chunks_to_qdrant(db_session, monkeypatch):
    project = seed_project(db_session)
    fake = FakeCodeIndex()
    _patch_index(monkeypatch, fake)

    result = sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[IndexFileInput(
            path="middleware/auth.py",
            content="def require_auth(request):\n    if not request.user:\n        raise Forbidden()\n",
        )],
    )

    assert result.chunks_created >= 1
    assert fake.ensure_called
    db_ids = {
        row.id for row in db_session.execute(select(CodeChunk)).scalars().all()
    }
    assert {p.id for p in fake.upserted} == db_ids
    assert {p.path for p in fake.upserted} == {"middleware/auth.py"}
    assert all(len(p.vector) == 768 for p in fake.upserted)
    assert all(p.project_id == project.id for p in fake.upserted)


def test_sync_succeeds_when_qdrant_unconfigured(db_session, monkeypatch):
    project = seed_project(db_session)
    _patch_index(monkeypatch, None)

    result = sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[IndexFileInput(path="app/a.py", content="x = 1\n")],
    )
    assert result.chunks_created >= 1
    total = db_session.execute(select(func.count()).select_from(CodeChunk)).scalar_one()
    assert total == result.chunks_created


def test_retrieve_prefers_qdrant(db_session, monkeypatch):
    project = seed_project(db_session)
    fake = FakeCodeIndex(hits=[
        QdrantHit(path="middleware/auth.py", start_line=1, end_line=3,
                  content="def require_auth(request):", score=0.91),
    ])
    _patch_index(monkeypatch, fake)

    items = retrieve_code_context(
        db_session, project_id=project.id, query_text="require auth guard"
    )
    assert len(items) == 1
    assert items[0].path == "middleware/auth.py"
    assert items[0].score == 0.91


def test_retrieve_falls_back_to_keyword_without_qdrant(db_session, monkeypatch):
    project = seed_project(db_session)
    _patch_index(monkeypatch, None)
    sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[IndexFileInput(
            path="middleware/auth.py",
            content="def require_auth(request):\n    if not request.user:\n        raise Forbidden()\n",
        )],
    )

    items = retrieve_code_context(
        db_session, project_id=project.id, query_text="authenticated users require auth guard"
    )
    assert items and items[0].path == "middleware/auth.py"


def test_build_code_points_skips_vectorless_rows():
    with_vector = CodeChunk(
        index_run_id="r", file_id="f", project_id="p", ordinal=0,
        start_line=1, end_line=2, content="x = 1",
        content_hash="h", embedding=[0.0, 0.1],
    )
    without_vector = CodeChunk(
        index_run_id="r", file_id="f", project_id="p", ordinal=1,
        start_line=3, end_line=4, content="y = 2",
        content_hash="h2", embedding=None,
    )
    points = build_code_points(
        [(with_vector, "app/a.py"), (without_vector, "app/a.py")], project_id="p"
    )
    assert len(points) == 1
    assert points[0].path == "app/a.py"
    assert points[0].vector == [0.0, 0.1]
