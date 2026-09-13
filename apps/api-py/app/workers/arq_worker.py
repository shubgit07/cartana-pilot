"""Arq background worker & job execution pipeline.

Arq (Asyncio Redis Queue) powers the background job pipeline.
Provides async job functions for:
  - run_ingest -> run_chunk -> run_embed -> run_extract_requirements

Also manages an in-memory & Redis job status registry for live status polling.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any, ClassVar

from arq.connections import RedisSettings
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.chunking import chunk_text
from app.core.dedupe import dedupe_key
from app.core.extract_text import extract_text
from app.db.models import (
    Chunk,
    Requirement,
    RequirementChunk,
    Source,
    SourceStatus,
)
from app.db.session import SessionLocal
from app.providers.ai_provider import (
    AIExtractRequirementsInput,
    get_ai_provider,
)
from app.providers.embedding_provider import get_embedding_provider
from app.providers.storage_provider import get_storage

logger = logging.getLogger(__name__)

# Job Status Registry
_job_status_registry: dict[str, dict[str, Any]] = {}


def set_job_status(job_id: str, state: str, result: Any = None, error: str | None = None) -> None:
    _job_status_registry[job_id] = {
        "jobId": job_id,
        "state": state,  # "pending", "processing", "completed", "failed"
        "result": result,
        "error": error,
    }


def get_job_status(job_id: str) -> dict[str, Any]:
    return _job_status_registry.get(
        job_id,
        {"jobId": job_id, "state": "UNKNOWN", "result": None, "error": None},
    )


# Helper for Source Status
def _mark_source_status(session: Session, source_id: str, status: SourceStatus, error: str | None = None) -> None:
    source = session.get(Source, source_id)
    if source is not None:
        source.status = status
        source.error_message = error
        session.commit()


def _mark_failed(session: Session, source_id: str, message: str) -> None:
    try:
        _mark_source_status(session, source_id, SourceStatus.FAILED, message)
    except Exception:
        session.rollback()
        logger.exception("could not record failure (source_id=%s)", source_id)


def _dedupe_chunk_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for cid in ids:
        if cid and cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def _cap_chunks_for_extract(chunks: list[Chunk], max_chars: int) -> list[Chunk]:
    """Bound the per-extraction LLM prompt to a character budget (cost control)."""
    total = 0
    capped: list[Chunk] = []
    for chunk in chunks:
        total += len(chunk.text)
        if total > max_chars:
            break
        capped.append(chunk)
    if len(capped) < len(chunks):
        logger.warning(
            "arq:extract:chunks truncated (%d/%d) beyond %d chars — trailing chunks dropped",
            len(capped),
            len(chunks),
            max_chars,
        )
    return capped


# ---- Core synchronous task execution logic ----

def execute_ingest_stage(source_id: str, project_id: str | None = None, user_id: str | None = None) -> str:
    """Stage 1: Load file, extract text."""
    logger.info("arq:ingest:start (source_id=%s)", source_id)
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

        logger.info("arq:ingest:done (source_id=%s, text_len=%d)", source_id, len(text))
        return text
    except Exception as exc:
        session.rollback()
        logger.exception("arq:ingest:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


def execute_chunk_stage(source_id: str, project_id: str, user_id: str, text: str) -> list[str]:
    """Stage 2: Split text into Chunk rows."""
    logger.info("arq:chunk:start (source_id=%s)", source_id)
    session = SessionLocal()
    try:
        # The project may have been deleted while ingestion was in flight —
        # skip instead of resurrecting orphan rows.
        if session.get(Source, source_id) is None:
            logger.info("arq:chunk:skip (source_id=%s, deleted)", source_id)
            return []
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
        logger.info("arq:chunk:done (source_id=%s, chunks=%d)", source_id, len(chunk_ids))
        return chunk_ids
    except Exception as exc:
        session.rollback()
        logger.exception("arq:chunk:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


def execute_embed_stage(source_id: str, project_id: str, user_id: str, chunk_ids: list[str]) -> int:
    """Stage 3: Embed chunks via embedding_provider."""
    logger.info("arq:embed:start (source_id=%s, chunks=%d)", source_id, len(chunk_ids))
    session = SessionLocal()
    try:
        chunks = session.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
        if not chunks:
            return 0

        provider = get_embedding_provider()
        vectors = provider.embed([c.text for c in chunks])

        for chunk, vec in zip(chunks, vectors):
            session.execute(
                update(Chunk).where(Chunk.id == chunk.id).values(embedding=vec)
            )

        session.commit()
        logger.info("arq:embed:done (source_id=%s, embedded=%d)", source_id, len(chunks))
        return len(chunks)
    except Exception as exc:
        session.rollback()
        logger.exception("arq:embed:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


def execute_extract_requirements_stage(source_id: str, project_id: str, user_id: str) -> int:
    """Stage 4: Extract requirements via AIProvider."""
    logger.info("arq:extract-reqs:start (source_id=%s)", source_id)
    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            logger.info("arq:extract-reqs:skip (source_id=%s, deleted)", source_id)
            return 0

        chunks = (
            session.query(Chunk)
            .filter(Chunk.source_id == source_id)
            .order_by(Chunk.position.asc())
            .all()
        )
        if not chunks:
            _mark_source_status(session, source_id, SourceStatus.PROCESSED, error=None)
            return 0

        chunks = _cap_chunks_for_extract(chunks, get_settings().extract_max_chars)
        if not chunks:
            _mark_source_status(session, source_id, SourceStatus.PROCESSED, error=None)
            return 0

        ai = get_ai_provider()
        extracted = ai.extract_requirements(
            AIExtractRequirementsInput(
                sourceFilename=source.filename,
                chunks=[{"id": c.id, "position": c.position, "text": c.text} for c in chunks],
            )
        )

        fresh_keys: set[str] = set()
        chunk_id_set = {c.id for c in chunks}

        for item in extracted:
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
                session.query(RequirementChunk).filter(
                    RequirementChunk.requirement_id == existing.id
                ).delete()
                for cid in _dedupe_chunk_ids(valid_chunk_ids):
                    session.add(RequirementChunk(requirement_id=existing.id, chunk_id=cid))
                existing.title = item.title
                existing.description = item.description
                session.commit()
                fresh_keys.add(key)

        _mark_source_status(session, source_id, SourceStatus.PROCESSED, error=None)
        logger.info("arq:extract-reqs:done (source_id=%s, extracted=%d)", source_id, len(extracted))
        return len(extracted)
    except Exception as exc:
        session.rollback()
        logger.exception("arq:extract-reqs:failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


def run_full_pipeline_sync(source_id: str, project_id: str, user_id: str) -> None:
    """Run the ingestion pipeline synchronously.

    The pipeline stops after requirement extraction and marks the source processed.
    """
    try:
        text = execute_ingest_stage(source_id, project_id, user_id)
        chunk_ids = execute_chunk_stage(source_id, project_id, user_id, text)
        execute_embed_stage(source_id, project_id, user_id, chunk_ids)
        execute_extract_requirements_stage(source_id, project_id, user_id)
    except Exception:
        logger.exception("Full pipeline failed for source %s", source_id)


def _run_pipeline_with_watchdog(source_id: str, project_id: str, user_id: str) -> None:
    """Run the ingest pipeline under an overall deadline.

    The frontend polls source status while it is ``processing``. If a stage
    hangs (slow external provider, dead worker thread), the source would
    otherwise stay ``processing`` forever and the UI would load indefinitely.
    On timeout we mark the source ``failed`` with a clear message so the UI
    stops polling and surfaces the error.
    """
    timeout = get_settings().ingest_timeout_seconds
    worker = threading.Thread(
        target=run_full_pipeline_sync,
        args=(source_id, project_id, user_id),
        daemon=True,
    )
    worker.start()
    worker.join(timeout=timeout)

    if worker.is_alive():
        logger.error("ingest timed out after %ds (source_id=%s)", timeout, source_id)
        session = SessionLocal()
        try:
            _mark_source_status(
                session,
                source_id,
                SourceStatus.FAILED,
                f"Ingest timed out after {timeout}s",
            )
        except Exception:
            session.rollback()
            logger.exception("could not mark ingest timeout (source_id=%s)", source_id)
        finally:
            session.close()


# ---- Async ARQ task functions ----

async def arq_run_ingest(ctx: dict, source_id: str, project_id: str, user_id: str) -> None:
    await asyncio.to_thread(_run_pipeline_with_watchdog, source_id, project_id, user_id)


# ---- Helper Enqueue Functions (called by API service layer) ----

def _spawn_background(fn: Callable[..., Any], *args: Any) -> None:
    """Run a sync job in a daemon thread so the caller never blocks."""
    threading.Thread(target=fn, args=args, daemon=True).start()


def enqueue_ingest(source_id: str, project_id: str, user_id: str) -> None:
    """Enqueue full ingestion job in background thread + ARQ task."""
    job_id = f"ingest-{source_id}"
    set_job_status(job_id, "processing")

    # Run immediately off the caller's thread so the request returns fast and
    # the frontend can poll job/source status for live progress. A watchdog
    # enforces an overall pipeline deadline so a stuck source can never keep
    # the UI loading forever.
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _run_pipeline_with_watchdog, source_id, project_id, user_id)
    except RuntimeError:
        # No running loop (e.g. sync thread context)
        _spawn_background(_run_pipeline_with_watchdog, source_id, project_id, user_id)


# ---- Arq WorkerSettings (for `arq app.workers.arq_worker.WorkerSettings`) ----

def _arq_redis_settings() -> RedisSettings:
    """Parse REDIS_URL properly (Upstash rediss:// URLs carry auth + TLS)."""
    from urllib.parse import urlsplit

    raw = (get_settings().redis_url or "").strip() or "redis://localhost:6379"
    parts = urlsplit(raw if "://" in raw else f"redis://{raw}")
    return RedisSettings(
        host=parts.hostname or "localhost",
        port=parts.port or 6379,
        password=parts.password,
        ssl=parts.scheme == "rediss",
    )


class WorkerSettings:
    functions: ClassVar[list[Any]] = [arq_run_ingest]
    redis_settings = _arq_redis_settings()
