"""Tests for the repository indexer (Phase 1) and code retrieval helper."""
from __future__ import annotations

from sqlalchemy import func, select

from app.api.services.repo_index_service import (
    IndexFileInput,
    format_code_context,
    is_indexable_path,
    retrieve_code_context,
    sync_repository_snapshot,
)
from app.core.chunking import chunk_code_lines as chunk_code_lines_core
from app.db.models import CodeChunk, IndexRun, RepositoryFile
from tests.conftest import seed_project


def test_is_indexable_path_filters_noise():
    assert is_indexable_path("app/service.py")
    assert is_indexable_path("src/auth.ts")
    assert not is_indexable_path("node_modules/react/index.js")
    assert not is_indexable_path("dist/bundle.js")
    assert not is_indexable_path("package-lock.json")
    assert not is_indexable_path("app.min.js")
    assert not is_indexable_path("logo.svg")


def test_chunk_code_lines_preserves_line_numbers():
    content = "\n".join(f"line {i}" for i in range(1, 151))
    pieces = chunk_code_lines_core(content, max_lines=60, overlap=10)
    assert len(pieces) >= 3
    assert pieces[0].start_line == 1
    for piece in pieces:
        assert piece.end_line >= piece.start_line
        assert piece.text.strip() != ""


def test_sync_repository_snapshot_indexes_and_skips_noise(db_session):
    project = seed_project(db_session)
    result = sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[
            IndexFileInput(path="app/auth.py", content="def login():\n    return True\n"),
            IndexFileInput(path="node_modules/x/index.js", content="noise"),
            IndexFileInput(path="app/auth.py", content="def login():\n    return True\n"),  # dupe
        ],
    )
    assert result.files_indexed == 1
    assert result.chunks_created >= 1
    assert any("node_modules" in s for s in result.skipped)

    files = db_session.execute(select(RepositoryFile)).scalars().all()
    assert len(files) == 1
    chunks = db_session.execute(select(CodeChunk)).scalars().all()
    assert len(chunks) == result.chunks_created
    assert chunks[0].start_line == 1

    # Re-sync with identical content is a no-op for chunks.
    again = sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[
            IndexFileInput(path="app/auth.py", content="def login():\n    return True\n"),
            IndexFileInput(path="node_modules/x/index.js", content="noise"),
        ],
    )
    assert again.files_indexed == 0
    total = db_session.execute(select(func.count()).select_from(CodeChunk)).scalar_one()
    assert total == result.chunks_created

    runs = db_session.execute(select(IndexRun)).scalars().all()
    assert len(runs) == 2
    assert all(r.status.value == "succeeded" for r in runs)


def test_retrieve_code_context_keyword_fallback(db_session):
    project = seed_project(db_session)
    sync_repository_snapshot(
        db_session,
        project_id=project.id,
        user_id=project.user_id,
        files=[
            IndexFileInput(
                path="middleware/auth.py",
                content="def require_auth(request):\n    if not request.user:\n        raise Forbidden()\n",
            ),
            IndexFileInput(
                path="services/refund_service.py",
                content="def issue_refund(order):\n    return charge(order)\n",
            ),
        ],
    )
    items = retrieve_code_context(
        db_session, project_id=project.id, query_text="authenticated users require auth guard"
    )
    assert items, "expected the auth chunk to match"
    assert items[0].path == "middleware/auth.py"
    assert format_code_context(items)


def test_retrieve_code_context_empty_without_index(db_session):
    project = seed_project(db_session)
    assert retrieve_code_context(db_session, project_id=project.id, query_text="refunds") == []
    assert retrieve_code_context(db_session, project_id=project.id, query_text="  ") == []
