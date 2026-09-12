"""Repository indexer: workspace snapshot → files → code chunks → embeddings.

Design notes (kept deliberately narrow):
- Input is an explicit ``[{path, content}]`` payload supplied by the caller.
  A future git-clone adapter can reuse this module by producing the same
  payload; no clone/network logic lives here.
- Noise filtering reuses ``IGNORED_RE`` from the diff parser so the index
  and the verifier agree on what is worth keeping.
- Embeddings go through :func:`get_embedding_provider` (stub in dev/tests,
  Cloudflare BGE 768-dim in prod). Vectors are cached per content hash by
  the provider layer when Redis is available.
- Postgres (Neon) is the source of truth for files, chunks, snapshots, and
  verdicts. **Qdrant is the primary vector index**: every embedded chunk is
  upserted as ``{id=CodeChunk.id, vector, payload}`` for semantic retrieval.
  Postgres ``Vector`` columns are never queried (no pgvector distance
  operators); they stay NULL-friendly for audit and keyword fallback.
- Re-syncs are idempotent: files with an unchanged ``contentHash`` are
  skipped, changed files are re-chunked, and a new ``IndexRun`` records
  each sync for auditability. Qdrant upserts are idempotent by point id.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.services.project_service import get_owned_project
from app.core.chunking import chunk_code_lines
from app.core.diff_parser import IGNORED_RE
from app.db.models import (
    CodeChunk,
    IndexRun,
    RepositoryConnection,
    RepositoryFile,
    RepositoryProvider,
    RepositorySnapshot,
    RunStatus,
    SnapshotKind,
)
from app.providers.embedding_provider import get_embedding_provider
from app.providers.qdrant_provider import build_code_points, get_code_index

logger = logging.getLogger(__name__)

INDEX_VERSION = "code-index-v1"
MAX_FILE_BYTES = 200_000
MAX_FILES = 500
EMBED_BATCH_SIZE = 32

_EXTRA_IGNORE_RE = re.compile(
    r"(^|/)\.git(/|$)|__pycache__|\.pyc$|\.pyo$|\.egg-info(/|$)|(^|/)\.venv(/|$)",
    re.IGNORECASE,
)

_LANGUAGE_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C", ".h": "C",
    ".swift": "Swift", ".kt": "Kotlin", ".sql": "SQL", ".sh": "Shell",
    ".md": "Markdown", ".txt": "Text", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".json": "JSON", ".css": "CSS", ".html": "HTML",
}


@dataclass
class IndexFileInput:
    path: str
    content: str


@dataclass
class IndexSyncResult:
    snapshot_id: str
    commit_sha: str
    files_indexed: int
    chunks_created: int
    skipped: list[str] = field(default_factory=list)
    embedding_model: str = ""
    embedding_dim: int = 768


def is_indexable_path(path: str) -> bool:
    """Mirror the diff noise filter plus build-artifact extras."""
    normalized = path.strip().lstrip("./").replace("\\", "/")
    if not normalized or normalized.startswith(".git/"):
        return False
    return not (IGNORED_RE.search(normalized) or _EXTRA_IGNORE_RE.search(normalized))


def detect_language(path: str) -> str | None:
    dot = path.rfind(".")
    if dot < 0:
        return None
    return _LANGUAGE_BY_EXT.get(path[dot:].lower())


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ensure_connection(db: Session, project_id: str, user_id: str) -> RepositoryConnection:
    existing = db.execute(
        select(RepositoryConnection).where(
            RepositoryConnection.project_id == project_id,
            RepositoryConnection.provider == RepositoryProvider.GENERIC_GIT,
            RepositoryConnection.external_id == "workspace",
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    connection = RepositoryConnection(
        project_id=project_id,
        user_id=user_id,
        provider=RepositoryProvider.GENERIC_GIT,
        external_id="workspace",
        clone_url="workspace://local",
        default_branch="main",
        display_name="Workspace snapshot",
        is_active=True,
    )
    db.add(connection)
    db.flush()
    return connection


def get_or_create_snapshot(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    connection: RepositoryConnection | None = None,
    commit_sha: str,
    ref_name: str | None = None,
    kind: SnapshotKind = SnapshotKind.COMMIT,
) -> RepositorySnapshot:
    """Fetch or create the snapshot row a verification run pins its evidence to."""
    connection = connection or _ensure_connection(db, project_id, user_id)
    snapshot = db.execute(
        select(RepositorySnapshot).where(
            RepositorySnapshot.repository_id == connection.id,
            RepositorySnapshot.commit_sha == commit_sha,
        )
    ).scalar_one_or_none()
    if snapshot is None:
        snapshot = RepositorySnapshot(
            repository_id=connection.id,
            project_id=project_id,
            user_id=user_id,
            kind=kind,
            commit_sha=commit_sha,
            ref_name=ref_name,
            committed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(snapshot)
        db.flush()
    return snapshot


def _mirror_chunks_to_qdrant(
    created_chunks: list[tuple[CodeChunk, str]], *, project_id: str
) -> None:
    """Best-effort Qdrant mirror of newly indexed chunks. Never raises."""
    try:
        index = get_code_index()
        if index is None:
            return
        points = build_code_points(created_chunks, project_id=project_id)
        if not points:
            return
        index.ensure_collection()
        mirrored = index.upsert_chunks(points)
        logger.info("Mirrored %d code chunks to Qdrant (project_id=%s).", mirrored, project_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant mirror failed, Postgres rows remain authoritative: %s", exc)


def sync_repository_snapshot(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    files: list[IndexFileInput],
    commit_sha: str | None = None,
    ref_name: str | None = None,
) -> IndexSyncResult:
    """Index a set of code files into CodeChunk rows. Idempotent per content hash."""
    get_owned_project(db, user_id, project_id)

    # Dedupe by normalized path; last occurrence wins.
    by_path: dict[str, str] = {}
    for item in files:
        normalized = item.path.strip().lstrip("./").replace("\\", "/")
        if normalized:
            by_path[normalized] = item.content

    if commit_sha:
        resolved_sha = commit_sha[:64]
    else:
        fingerprint = "\n".join(f"{p}:{_sha256_hex(c)}" for p, c in sorted(by_path.items()))
        resolved_sha = _sha256_hex(fingerprint)[:40]

    connection = _ensure_connection(db, project_id, user_id)
    snapshot = get_or_create_snapshot(
        db,
        project_id=project_id,
        user_id=user_id,
        connection=connection,
        commit_sha=resolved_sha,
        ref_name=ref_name,
        kind=SnapshotKind.COMMIT,
    )

    provider = get_embedding_provider()
    index_run = IndexRun(
        snapshot_id=snapshot.id,
        project_id=project_id,
        user_id=user_id,
        status=RunStatus.RUNNING,
        index_version=INDEX_VERSION,
        embedding_model=provider.id,
        embedding_dimension=provider.dim,
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(index_run)
    db.flush()

    skipped: list[str] = []
    files_indexed = 0
    chunks_created = 0
    pending_texts: list[str] = []
    pending_meta: list[tuple[RepositoryFile, int, int, int, str]] = []
    created_chunks: list[tuple[CodeChunk, str]] = []

    candidates = list(by_path.items())[:MAX_FILES]
    if len(by_path) > MAX_FILES:
        skipped.append(f"... and {len(by_path) - MAX_FILES} more files over the {MAX_FILES} cap")

    for path, content in candidates:
        if not is_indexable_path(path):
            skipped.append(f"{path} (ignored)")
            continue
        size_bytes = len(content.encode("utf-8", errors="ignore"))
        if size_bytes > MAX_FILE_BYTES:
            skipped.append(f"{path} (oversize {size_bytes}B)")
            continue
        if "\x00" in content:
            skipped.append(f"{path} (binary)")
            continue

        content_hash = _sha256_hex(content)
        line_count = content.count("\n") + (0 if content.endswith("\n") or not content else 1)

        record = db.execute(
            select(RepositoryFile).where(
                RepositoryFile.snapshot_id == snapshot.id,
                RepositoryFile.path == path,
            )
        ).scalar_one_or_none()
        if record is not None and record.content_hash == content_hash:
            continue  # Unchanged since last sync — chunks already stored.
        if record is None:
            record = RepositoryFile(
                snapshot_id=snapshot.id,
                project_id=project_id,
                path=path,
                blob_sha=content_hash,
                content_hash=content_hash,
                language=detect_language(path),
                size_bytes=size_bytes,
                line_count=line_count,
                is_binary=False,
            )
            db.add(record)
            db.flush()
        else:
            db.execute(delete(CodeChunk).where(CodeChunk.file_id == record.id))
            record.blob_sha = content_hash
            record.content_hash = content_hash
            record.language = detect_language(path)
            record.size_bytes = size_bytes
            record.line_count = line_count
            db.flush()

        pieces = chunk_code_lines(content)
        if not pieces:
            skipped.append(f"{path} (empty)")
            continue
        files_indexed += 1
        for ordinal, piece in enumerate(pieces):
            pending_texts.append(piece.text)
            pending_meta.append(
                (record, ordinal, piece.start_line, piece.end_line, piece.text)
            )

    try:
        vectors: list[list[float] | None] = [None] * len(pending_texts)
        for start in range(0, len(pending_texts), EMBED_BATCH_SIZE):
            batch = pending_texts[start:start + EMBED_BATCH_SIZE]
            if batch:
                vectors[start:start + len(batch)] = provider.embed(batch)
    except Exception as exc:  # noqa: BLE001 — indexing must degrade, not crash sync
        logger.warning("Embedding %d texts failed, storing chunks without vectors: %s", len(pending_texts), exc)
        vectors = [None] * len(pending_texts)

    for (record, ordinal, start_line, end_line, text), vector in zip(pending_meta, vectors):
        chunk = CodeChunk(
            index_run_id=index_run.id,
            file_id=record.id,
            project_id=project_id,
            ordinal=ordinal,
            start_line=start_line,
            end_line=end_line,
            content=text,
            content_hash=_sha256_hex(f"{record.path}:{ordinal}:{text}"),
            token_count=max(1, len(text) // 4),
            embedding=vector,
        )
        db.add(chunk)
        created_chunks.append((chunk, record.path))
        chunks_created += 1

    index_run.status = RunStatus.SUCCEEDED
    index_run.completed_at = datetime.now(UTC).replace(tzinfo=None)
    index_run.stats = {
        "filesIndexed": files_indexed,
        "chunksCreated": chunks_created,
        "skipped": len(skipped),
    }
    db.commit()

    _mirror_chunks_to_qdrant(created_chunks, project_id=project_id)

    return IndexSyncResult(
        snapshot_id=snapshot.id,
        commit_sha=resolved_sha,
        files_indexed=files_indexed,
        chunks_created=chunks_created,
        skipped=skipped,
        embedding_model=provider.id,
        embedding_dim=provider.dim,
    )


@dataclass
class CodeContextItem:
    path: str
    start_line: int
    end_line: int
    content: str
    score: float


def retrieve_code_context(
    db: Session,
    *,
    project_id: str,
    query_text: str,
    top_k: int = 3,
    max_chars: int = 3000,
) -> list[CodeContextItem]:
    """Hybrid retrieval: Qdrant vectors first, keyword fallback otherwise.

    Postgres is never queried by vector (no pgvector distance operators):
    Neon runs the relational schema only. Never raises — verification works
    diff-only when the index is empty or Qdrant is unreachable.
    """
    query = query_text.strip()
    if not query:
        return []
    try:
        qdrant_items = _retrieve_code_context_qdrant(
            project_id=project_id, query=query, top_k=top_k
        )
        if qdrant_items:
            return qdrant_items
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant retrieval failed, falling back to keyword: %s", exc)
    try:
        return _retrieve_code_context_keyword(db, project_id=project_id, query=query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Code context retrieval failed, continuing diff-only: %s", exc)
        return []


def _retrieve_code_context_qdrant(
    *, project_id: str, query: str, top_k: int
) -> list[CodeContextItem]:
    """Cosine search over the Qdrant code index. Empty list when unconfigured."""
    index = get_code_index()
    if index is None:
        return []
    vectors = get_embedding_provider().embed([query])
    if not vectors:
        return []
    return [
        CodeContextItem(
            path=hit.path,
            start_line=hit.start_line,
            end_line=hit.end_line,
            content=hit.content,
            score=hit.score,
        )
        for hit in index.search(project_id=project_id, vector=vectors[0], top_k=top_k)
    ]


def _retrieve_code_context_keyword(
    db: Session, *, project_id: str, query: str, top_k: int
) -> list[CodeContextItem]:
    """Token-overlap fallback over Postgres rows (no vector operators)."""
    tokens = {t for t in query.lower().split() if len(t) > 2}
    if not tokens:
        return []
    rows = db.execute(
        select(CodeChunk, RepositoryFile.path)
        .join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id)
        .where(CodeChunk.project_id == project_id)
        .limit(500)
    ).all()
    scored: list[tuple[float, CodeChunk, str]] = []
    for chunk, path in rows:
        haystack = f"{path}\n{chunk.content}".lower()
        hits = sum(1 for t in tokens if t in haystack)
        if hits:
            scored.append((hits / len(tokens), chunk, path))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        CodeContextItem(
            path=path, start_line=chunk.start_line, end_line=chunk.end_line,
            content=chunk.content, score=score,
        )
        for score, chunk, path in scored[:top_k]
    ]


def format_code_context(items: list[CodeContextItem], *, max_chars: int = 3000) -> str:
    """Render retrieved chunks as a compact, line-cited context block."""
    blocks: list[str] = []
    used = 0
    for item in items:
        block = (
            f"FILE: {item.path} [lines {item.start_line}-{item.end_line} | "
            f"relevance {item.score:.2f}]\n{item.content}"
        )
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 200:
                blocks.append(block[:remaining] + "\n…(truncated)")
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks)
