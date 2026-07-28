"""Full ingest pipeline — chunk → embed → extract requirements → extract tasks.

Port of the BullMQ job chain in ``apps/api/src/jobs/``. Each stage is a Celery
task that does its work and enqueues the next stage. The chain is:

    run_ingest → run_chunk → run_embed → run_extract_requirements → run_extract_tasks

All stages are idempotent: re-running on the same source preserves user edits
and marks superseded AI suggestions as rejected.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.chunking import chunk_text
from app.core.dedupe import dedupe_key
from app.core.errors import NotFoundError
from app.core.extract_text import extract_text
from app.db.models import (
    Chunk,
    Requirement,
    RequirementChunk,
    Source,
    SourceStatus,
    Task,
    TaskChunk,
)
from app.db.session import SessionLocal
from app.providers.ai_provider import (
    AIExtractRequirementsInput,
    AIExtractTasksInput,
    get_ai_provider,
)
from app.providers.embedding_provider import get_embedding_provider, to_pg_vector_literal
from app.providers.storage_provider import get_storage
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ---- Shared helpers ----


def _mark_source_status(session: Session, source_id: str, status: SourceStatus, error: Optional[str] = None) -> None:
    source = session.get(Source, source_id)
    if source is not None:
        source.status = status
        source.error_message = error
        session.commit()


def _mark_failed(session: Session, source_id: str, message: str) -> None:
    try:
        _mark_source_status(session, source_id, SourceStatus.FAILED, message)
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("could not record failure (source_id=%s)", source_id)


# ---- Stage 1: Ingest (extract text) ----


INGEST_TASK_NAME = "sources.ingest"


@celery_app.task(name=INGEST_TASK_NAME)
def run_ingest(source_id: str, project_id: Optional[str] = None, user_id: Optional[str] = None) -> dict[str, Any]:
    """Load file from storage, extract text, enqueue chunk stage."""
    logger.info("ingest:start (source_id=%s)", source_id)

    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError(f"Source {source_id} not found")

        _mark_source_status(session, source_id, SourceStatus.PROCESSING, error=None)

        storage = get_storage()
        data = storage.read(source.storage_key)
        text = extract_text(data, source.kind.value)

        if not text or not text.strip():
            raise RuntimeError("No extractable text found in source")

        logger.info("ingest:done (source_id=%s, text_len=%d)", source_id, len(text))

        # Enqueue chunk stage with the extracted text
        run_chunk.apply_async(
            kwargs={
                "source_id": source_id,
                "project_id": project_id or source.project_id,
                "user_id": user_id or source.user_id,
                "text": text,
            },
            task_id=f"chunk-{source_id}",
        )
        return {"sourceId": source_id, "status": SourceStatus.PROCESSING.value}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("ingest:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


# ---- Stage 2: Chunk (split text into Chunk rows) ----


CHUNK_TASK_NAME = "sources.chunk"


@celery_app.task(name=CHUNK_TASK_NAME)
def run_chunk(source_id: str, project_id: str, user_id: str, text: str) -> dict[str, Any]:
    """Split text into Chunk rows and enqueue embed stage."""
    logger.info("chunk:start (source_id=%s)", source_id)

    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError(f"Source {source_id} not found")

        # Idempotent: drop existing chunks for this source first
        session.query(Chunk).filter(Chunk.source_id == source_id).delete()
        session.commit()

        pieces = chunk_text(text)
        if not pieces:
            raise RuntimeError("Chunker produced 0 pieces from extracted text")

        chunks: list[Chunk] = []
        for piece in pieces:
            chunk = Chunk(source_id=source_id, position=piece.position, text=piece.text)
            session.add(chunk)
            chunks.append(chunk)
        session.commit()

        chunk_ids = [c.id for c in chunks]

        # Enqueue embed stage
        run_embed.apply_async(
            kwargs={
                "source_id": source_id,
                "project_id": project_id,
                "user_id": user_id,
                "chunk_ids": chunk_ids,
            },
            task_id=f"embed-{source_id}",
        )
        logger.info("chunk:done (source_id=%s, chunks=%d)", source_id, len(chunks))
        return {"sourceId": source_id, "chunks": len(chunks)}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("chunk:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


# ---- Stage 3: Embed (generate embeddings + store in pgvector) ----


EMBED_TASK_NAME = "sources.embed"


@celery_app.task(name=EMBED_TASK_NAME)
def run_embed(source_id: str, project_id: str, user_id: str, chunk_ids: list[str]) -> dict[str, Any]:
    """Generate embeddings for chunks and store them in pgvector."""
    logger.info("embed:start (source_id=%s, chunks=%d)", source_id, len(chunk_ids))

    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError(f"Source {source_id} not found")

        provider = get_embedding_provider()

        chunks = session.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
        if not chunks:
            return {"sourceId": source_id, "embedded": 0}

        vectors = provider.embed([c.text for c in chunks])

        # Write embeddings via raw SQL (pgvector column)
        for chunk, vec in zip(chunks, vectors):
            lit = to_pg_vector_literal(vec)
            session.execute(
                Chunk.__table__.update()
                .where(Chunk.__table__.c.id == chunk.id)
                .values(embedding=lit)
            )

        _mark_source_status(session, source_id, SourceStatus.PROCESSED, error=None)
        logger.info("embed:done (source_id=%s, embedded=%d)", source_id, len(chunks))

        # Enqueue requirement extraction
        run_extract_requirements.apply_async(
            kwargs={"source_id": source_id, "project_id": project_id, "user_id": user_id},
            task_id=f"extract-reqs-{source_id}",
        )
        return {"sourceId": source_id, "embedded": len(chunks)}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("embed:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


# ---- Stage 4: Extract Requirements ----


EXTRACT_REQS_TASK_NAME = "sources.extract_requirements"


@celery_app.task(name=EXTRACT_REQS_TASK_NAME)
def run_extract_requirements(source_id: str, project_id: str, user_id: str) -> dict[str, Any]:
    """Run AI requirement extraction, idempotent upsert, then enqueue task extraction."""
    logger.info("extract-reqs:start (source_id=%s)", source_id)

    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError(f"Source {source_id} not found")

        chunks = (
            session.query(Chunk)
            .filter(Chunk.source_id == source_id)
            .order_by(Chunk.position.asc())
            .all()
        )
        if not chunks:
            logger.warning("extract-reqs: no chunks, skipping (source_id=%s)", source_id)
            return {"sourceId": source_id, "extracted": 0}

        ai = get_ai_provider()
        extracted = ai.extract_requirements(
            AIExtractRequirementsInput(
                sourceFilename=source.filename,
                chunks=[{"id": c.id, "position": c.position, "text": c.text} for c in chunks],
            )
        )

        fresh_keys: set[str] = set()

        for item in extracted:
            # Filter to chunkIds that belong to this source
            chunk_id_set = {c.id for c in chunks}
            valid_chunk_ids = [cid for cid in item.chunkIds if cid in chunk_id_set]
            if not valid_chunk_ids:
                valid_chunk_ids = [chunks[0].id]

            key = dedupe_key(source_id, item.title)
            existing = (
                session.query(Requirement)
                .filter(Requirement.dedupe_key == key, Requirement.project_id == project_id)
                .first()
            )

            if existing is None:
                req = Requirement(
                    project_id=project_id,
                    user_id=user_id,
                    title=item.title,
                    description=item.description,
                    origin="ai",
                    state="suggested",
                    dedupe_key=key,
                )
                session.add(req)
                session.flush()
                for cid in _dedupe_chunk_ids(valid_chunk_ids):
                    session.add(RequirementChunk(requirement_id=req.id, chunk_id=cid))
                session.commit()
                fresh_keys.add(key)
            elif existing.state == "suggested" and existing.origin == "ai":
                # Still AI-suggested and untouched — refresh content + chunk links
                session.query(RequirementChunk).filter(
                    RequirementChunk.requirement_id == existing.id
                ).delete()
                for cid in _dedupe_chunk_ids(valid_chunk_ids):
                    session.add(RequirementChunk(requirement_id=existing.id, chunk_id=cid))
                existing.title = item.title
                existing.description = item.description
                session.commit()
                fresh_keys.add(key)
            # If user touched it, leave alone

        # Stale-out: mark AI suggestions not in fresh set as rejected
        _stale_out_ai_requirements(session, user_id, project_id, source_id, fresh_keys)

        logger.info("extract-reqs:done (source_id=%s, extracted=%d)", source_id, len(extracted))

        # Enqueue task extraction
        run_extract_tasks.apply_async(
            kwargs={"source_id": source_id, "project_id": project_id, "user_id": user_id},
            task_id=f"extract-tasks-{source_id}",
        )
        return {"sourceId": source_id, "extracted": len(extracted)}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("extract-reqs:failed (source_id=%s)", source_id)
        raise
    finally:
        session.close()


# ---- Stage 5: Extract Tasks ----


EXTRACT_TASKS_TASK_NAME = "sources.extract_tasks"


@celery_app.task(name=EXTRACT_TASKS_TASK_NAME)
def run_extract_tasks(source_id: str, project_id: str, user_id: str) -> dict[str, Any]:
    """Run AI task extraction, idempotent upsert with requirement linking."""
    logger.info("extract-tasks:start (source_id=%s)", source_id)

    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError(f"Source {source_id} not found")

        chunks = (
            session.query(Chunk)
            .filter(Chunk.source_id == source_id)
            .order_by(Chunk.position.asc())
            .all()
        )
        if not chunks:
            logger.warning("extract-tasks: no chunks, skipping (source_id=%s)", source_id)
            return {"sourceId": source_id, "extracted": 0}

        # Build title → id map for requirements linked to this source
        req_rows = (
            session.query(Requirement)
            .join(RequirementChunk, RequirementChunk.requirement_id == Requirement.id)
            .join(Chunk, Chunk.id == RequirementChunk.chunk_id)
            .filter(Chunk.source_id == source_id, Requirement.project_id == project_id)
            .distinct()
            .all()
        )
        requirement_id_by_title: dict[str, str] = {}
        requirement_payload: list[dict[str, str]] = []
        for r in req_rows:
            requirement_id_by_title[r.title.lower().strip()] = r.id
            requirement_payload.append({"title": r.title, "description": ""})

        ai = get_ai_provider()
        extracted = ai.extract_tasks(
            AIExtractTasksInput(
                sourceFilename=source.filename,
                chunks=[{"id": c.id, "position": c.position, "text": c.text} for c in chunks],
                requirements=requirement_payload,
            )
        )

        fresh_keys: set[str] = set()

        for item in extracted:
            chunk_id_set = {c.id for c in chunks}
            valid_chunk_ids = [cid for cid in item.chunkIds if cid in chunk_id_set]
            if not valid_chunk_ids:
                valid_chunk_ids = [chunks[0].id]

            linked_req_id: Optional[str] = None
            if item.linkedRequirementTitle:
                linked_req_id = requirement_id_by_title.get(item.linkedRequirementTitle.lower().strip())

            key = dedupe_key(source_id, item.title)
            existing = (
                session.query(Task)
                .filter(Task.dedupe_key == key, Task.project_id == project_id)
                .first()
            )

            if existing is None:
                task = Task(
                    project_id=project_id,
                    user_id=user_id,
                    title=item.title,
                    description=item.description,
                    origin="ai",
                    state="suggested",
                    dedupe_key=key,
                    requirement_id=linked_req_id,
                )
                session.add(task)
                session.flush()
                for cid in _dedupe_chunk_ids(valid_chunk_ids):
                    session.add(TaskChunk(task_id=task.id, chunk_id=cid))
                session.commit()
                fresh_keys.add(key)
            elif existing.state == "suggested" and existing.origin == "ai":
                session.query(TaskChunk).filter(TaskChunk.task_id == existing.id).delete()
                for cid in _dedupe_chunk_ids(valid_chunk_ids):
                    session.add(TaskChunk(task_id=existing.id, chunk_id=cid))
                existing.title = item.title
                existing.description = item.description
                existing.requirement_id = existing.requirement_id or linked_req_id
                session.commit()
                fresh_keys.add(key)

        # Stale-out
        _stale_out_ai_tasks(session, user_id, project_id, source_id, fresh_keys)

        logger.info("extract-tasks:done (source_id=%s, extracted=%d)", source_id, len(extracted))
        return {"sourceId": source_id, "extracted": len(extracted)}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("extract-tasks:failed (source_id=%s)", source_id)
        raise
    finally:
        session.close()


# ---- Stage 6: Run Audit (triggered manually) ----


RUN_AUDIT_TASK_NAME = "audit.run"


@celery_app.task(name=RUN_AUDIT_TASK_NAME)
def run_audit_task(project_id: str, user_id: str, source_id: str = "") -> dict[str, Any]:
    """Run the coverage audit engine. Triggered manually via POST /audit/run."""
    logger.info("audit:start (project_id=%s)", project_id)

    from app.api.services.audit_service import run_audit as _run_audit

    session = SessionLocal()
    try:
        run_id = _run_audit(session, user_id, project_id)
        logger.info("audit:done (project_id=%s, run_id=%s)", project_id, run_id)
        return {"runId": run_id}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("audit:failed (project_id=%s)", project_id)
        raise
    finally:
        session.close()


# ---- Stale-out helpers ----


def _stale_out_ai_requirements(
    session: Session,
    user_id: str,
    project_id: str,
    source_id: str,
    fresh_keys: set[str],
) -> int:
    """Mark AI-suggested requirements for source_id not in fresh_keys as rejected."""
    links = (
        session.query(RequirementChunk.requirement_id)
        .join(Chunk, Chunk.id == RequirementChunk.chunk_id)
        .filter(Chunk.source_id == source_id)
        .distinct()
        .all()
    )
    req_ids = {row[0] for row in links}

    stale_ids: list[str] = []
    for rid in req_ids:
        req = session.get(Requirement, rid)
        if req is None:
            continue
        if req.origin != "ai" or req.state != "suggested":
            continue
        if req.dedupe_key and req.dedupe_key not in fresh_keys:
            stale_ids.append(req.id)

    if stale_ids:
        session.query(Requirement).filter(
            Requirement.id.in_(stale_ids),
            Requirement.user_id == user_id,
            Requirement.project_id == project_id,
        ).update({"state": "rejected"}, synchronize_session=False)
        session.commit()

    return len(stale_ids)


def _stale_out_ai_tasks(
    session: Session,
    user_id: str,
    project_id: str,
    source_id: str,
    fresh_keys: set[str],
) -> int:
    """Mark AI-suggested tasks for source_id not in fresh_keys as rejected."""
    links = (
        session.query(TaskChunk.task_id)
        .join(Chunk, Chunk.id == TaskChunk.chunk_id)
        .filter(Chunk.source_id == source_id)
        .distinct()
        .all()
    )
    task_ids = {row[0] for row in links}

    stale_ids: list[str] = []
    for tid in task_ids:
        task = session.get(Task, tid)
        if task is None:
            continue
        if task.origin != "ai" or task.state != "suggested":
            continue
        if task.dedupe_key and task.dedupe_key not in fresh_keys:
            stale_ids.append(task.id)

    if stale_ids:
        session.query(Task).filter(
            Task.id.in_(stale_ids),
            Task.user_id == user_id,
            Task.project_id == project_id,
        ).update({"state": "rejected"}, synchronize_session=False)
        session.commit()

    return len(stale_ids)


def _dedupe_chunk_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for cid in ids:
        if cid and cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


# ---- Enqueue helper (called by source_service on upload) ----


def enqueue_ingest(source_id: str, project_id: str, user_id: str) -> None:
    """Queue ingestion for a source.

    A broker outage must not fail the upload request: the row is already
    persisted with status ``uploaded`` and can be re-queued later.
    """
    try:
        run_ingest.apply_async(
            kwargs={"source_id": source_id, "project_id": project_id, "user_id": user_id},
            task_id=f"ingest-{source_id}",
        )
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception(
            "could not enqueue ingest job (source_id=%s)", source_id
        )


def enqueue_audit(project_id: str, user_id: str) -> str | None:
    """Queue an audit run. Returns the job ID or None if enqueue fails."""
    try:
        result = run_audit_task.apply_async(
            kwargs={"project_id": project_id, "user_id": user_id, "source_id": ""},
        )
        return result.id
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception(
            "could not enqueue audit job (project_id=%s)", project_id
        )
        return None
