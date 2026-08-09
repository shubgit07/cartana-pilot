"""Sources module - service layer (DB + storage access lives here).

Port of ``apps/api/src/modules/sources/service.ts``. Uploads are written to
the configured :class:`~app.providers.storage_provider.StorageProvider`, the
row is persisted with status ``uploaded``, and ingestion runs asynchronously
via ARQ - nothing in this module processes file contents.

Every lookup is scoped by ``user_id`` (and by ``project_id`` where the route
provides one), so a caller can never reach another user's sources.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.source import CreateSourceFromText, JobStatusView, SourceSummary
from app.api.services.project_service import get_owned_project
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.db.models import Chunk, Source, SourceKind, SourceStatus
from app.providers.storage_provider import build_storage_key, get_storage
from app.workers.tasks.ingest import enqueue_ingest

logger = logging.getLogger(__name__)

# Matches the 25MB multer limit of the Node upload route.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_TEXT_EXTENSIONS = (".txt", ".md", ".markdown")

_CHUNK_COUNT = (
    select(func.count(Chunk.id)).where(Chunk.source_id == Source.id).correlate(Source).scalar_subquery()
)


def infer_kind(filename: str, mime_type: str | None = None) -> SourceKind:
    """Map a filename / MIME type onto a supported source kind."""
    name = filename.lower()
    if name.endswith(".pdf") or mime_type == "application/pdf":
        return SourceKind.PDF
    if name.endswith(_TEXT_EXTENSIONS) or (mime_type or "").startswith("text/"):
        return SourceKind.TEXT
    raise ValidationError(f"Unsupported file type: {filename} ({mime_type or 'unknown'})")


def _validate_upload(data: bytes) -> None:
    if not data:
        raise ValidationError("Uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit"
        )


def _remove_quietly(storage_key: str) -> None:
    """Best-effort file cleanup; storage problems must not break the request."""
    try:
        get_storage().remove(storage_key)
    except Exception:
        logger.warning("could not remove stored file (key=%s)", storage_key, exc_info=True)


def _count_chunks(db: Session, source_id: str) -> int:
    return int(
        db.execute(select(func.count(Chunk.id)).where(Chunk.source_id == source_id)).scalar_one()
    )


def _get_owned_source(
    db: Session,
    user_id: str,
    source_id: str,
    project_id: str | None = None,
) -> Source:
    source = db.execute(
        select(Source).where(Source.id == source_id, Source.user_id == user_id)
    ).scalar_one_or_none()
    if source is None:
        raise NotFoundError("Source not found")
    if project_id is not None and source.project_id != project_id:
        raise ValidationError("Source does not belong to this project")
    return source


def _persist_source(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    filename: str,
    data: bytes,
    kind: SourceKind,
    mime_type: str | None,
) -> SourceSummary:
    storage_key = get_storage().save(build_storage_key(project_id, filename), data)

    source = Source(
        project_id=project_id,
        user_id=user_id,
        filename=filename,
        kind=kind,
        status=SourceStatus.UPLOADED,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=len(data),
    )
    db.add(source)
    try:
        db.commit()
    except Exception:
        db.rollback()
        _remove_quietly(storage_key)  # never leave an orphaned file behind
        raise
    db.refresh(source)

    enqueue_ingest(source_id=source.id, project_id=project_id, user_id=user_id)
    return SourceSummary.from_model(source, chunk_count=0)


def list_sources(db: Session, user_id: str, project_id: str) -> list[SourceSummary]:
    rows = db.execute(
        select(Source, _CHUNK_COUNT.label("chunk_count"))
        .where(Source.project_id == project_id, Source.user_id == user_id)
        .order_by(Source.created_at.desc())
    ).all()
    return [SourceSummary.from_model(source, chunk_count) for source, chunk_count in rows]


def get_source(
    db: Session,
    user_id: str,
    source_id: str,
    project_id: str | None = None,
) -> SourceSummary:
    source = _get_owned_source(db, user_id, source_id, project_id)
    return SourceSummary.from_model(source, _count_chunks(db, source.id))


def create_source_from_file(
    db: Session,
    user_id: str,
    project_id: str,
    *,
    filename: str,
    data: bytes,
    mime_type: str | None = None,
) -> SourceSummary:
    get_owned_project(db, user_id, project_id)
    _validate_upload(data)

    return _persist_source(
        db,
        user_id=user_id,
        project_id=project_id,
        filename=filename,
        data=data,
        kind=infer_kind(filename, mime_type),
        mime_type=mime_type,
    )


def create_source_from_text(
    db: Session,
    user_id: str,
    project_id: str,
    payload: CreateSourceFromText,
) -> SourceSummary:
    get_owned_project(db, user_id, project_id)
    data = payload.content.encode("utf-8")
    _validate_upload(data)

    return _persist_source(
        db,
        user_id=user_id,
        project_id=project_id,
        filename=payload.filename,
        data=data,
        kind=SourceKind.TEXT,
        mime_type="text/plain",
    )


def get_source_job_status(
    db: Session,
    user_id: str,
    source_id: str,
    project_id: str | None = None,
) -> JobStatusView:
    source = _get_owned_source(db, user_id, source_id, project_id)
    chunks_total = _count_chunks(db, source.id)
    embedded = int(
        db.execute(
            select(func.count(Chunk.id)).where(
                Chunk.source_id == source.id, Chunk.embedding.is_not(None)
            )
        ).scalar_one()
    )
    return JobStatusView.from_model(source, chunks_total=chunks_total, embedded=embedded)


def delete_source(
    db: Session,
    user_id: str,
    source_id: str,
    project_id: str | None = None,
) -> None:
    source = _get_owned_source(db, user_id, source_id, project_id)
    storage_key = source.storage_key
    db.delete(source)
    db.commit()
    _remove_quietly(storage_key)
