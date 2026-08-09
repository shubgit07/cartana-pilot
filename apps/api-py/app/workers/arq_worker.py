"""Arq background worker & job execution pipeline.

Arq (Asyncio Redis Queue) powers the background job pipeline.
Provides async job functions for:
  - run_ingest -> run_chunk -> run_embed -> run_extract_requirements
  - run_task_generation (on-demand, for processed sources)
  - run_audit_task

Also manages an in-memory & Redis job status registry for live status polling.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Callable
from typing import Any, ClassVar

from arq.connections import RedisSettings
from sqlalchemy import select
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
    Task,
    TaskChunk,
)
from app.db.session import SessionLocal
from app.providers.ai_provider import (
    AIExtractRequirementsInput,
    AIExtractTasksInput,
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
                Chunk.__table__.update()
                .where(Chunk.__table__.c.id == chunk.id)
                .values(embedding=vec)
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
            raise RuntimeError(f"Source {source_id} not found")

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


def execute_extract_tasks_stage(source_id: str, project_id: str, user_id: str) -> int:
    """Stage 5: Extract tasks via AIProvider."""
    logger.info("arq:extract-tasks:start (source_id=%s)", source_id)
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
            return 0

        chunks = _cap_chunks_for_extract(chunks, get_settings().extract_max_chars)
        if not chunks:
            return 0

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

        chunk_id_set = {c.id for c in chunks}

        for item in extracted:
            valid_chunk_ids = [cid for cid in item.chunkIds if cid in chunk_id_set]
            if not valid_chunk_ids:
                valid_chunk_ids = [chunks[0].id]

            linked_req_id: str | None = None
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
            elif existing.state == "suggested" and existing.origin == "ai":
                session.query(TaskChunk).filter(TaskChunk.task_id == existing.id).delete()
                for cid in _dedupe_chunk_ids(valid_chunk_ids):
                    session.add(TaskChunk(task_id=existing.id, chunk_id=cid))
                existing.title = item.title
                existing.description = item.description
                existing.requirement_id = existing.requirement_id or linked_req_id
                session.commit()

        logger.info("arq:extract-tasks:done (source_id=%s, extracted=%d)", source_id, len(extracted))
        return len(extracted)
    except Exception:
        session.rollback()
        logger.exception("arq:extract-tasks:failed (source_id=%s)", source_id)
        raise
    finally:
        session.close()


def run_full_pipeline_sync(source_id: str, project_id: str, user_id: str) -> None:
    """Run the ingestion pipeline synchronously.

    Auto path stops after requirement extraction (source marked ``processed``).
    Task extraction is deferred to on-demand generation.
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


def run_audit_sync(project_id: str, user_id: str, job_id: str) -> str:
    """Run full audit engine synchronously and update job status."""
    from app.api.services.audit_service import run_audit as _run_audit
    session = SessionLocal()
    try:
        set_job_status(job_id, "processing")
        run_id = _run_audit(session, user_id, project_id)
        set_job_status(job_id, "completed", result={"runId": run_id})
        return run_id
    except Exception as exc:
        session.rollback()
        logger.exception("Audit failed for project %s", project_id)
        set_job_status(job_id, "failed", error=str(exc))
        raise
    finally:
        session.close()


def run_task_generation_sync(project_id: str, user_id: str, job_id: str) -> int:
    """Generate tasks for every processed source in a project, synchronously."""
    session = SessionLocal()
    try:
        set_job_status(job_id, "processing")
        source_ids = [
            row[0]
            for row in session.execute(
                select(Source.id).where(
                    Source.project_id == project_id,
                    Source.user_id == user_id,
                    Source.status == SourceStatus.PROCESSED,
                )
            ).all()
        ]
        total = 0
        for source_id in source_ids:
            total += execute_extract_tasks_stage(source_id, project_id, user_id)
        set_job_status(job_id, "completed", result={"generated": total})
        return total
    except Exception as exc:
        session.rollback()
        logger.exception("Task generation failed for project %s", project_id)
        set_job_status(job_id, "failed", error=str(exc))
        raise
    finally:
        session.close()


# ---- Async ARQ task functions ----

async def arq_run_ingest(ctx: dict, source_id: str, project_id: str, user_id: str) -> None:
    await asyncio.to_thread(_run_pipeline_with_watchdog, source_id, project_id, user_id)


async def arq_run_audit(ctx: dict, project_id: str, user_id: str, job_id: str) -> str:
    return await asyncio.to_thread(run_audit_sync, project_id, user_id, job_id)


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


def enqueue_audit(project_id: str, user_id: str) -> str:
    """Enqueue audit run. Returns job_id."""
    job_id = str(uuid.uuid4())
    set_job_status(job_id, "pending")

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, run_audit_sync, project_id, user_id, job_id)
    except RuntimeError:
        _spawn_background(run_audit_sync, project_id, user_id, job_id)

    return job_id


def enqueue_task_generation(project_id: str, user_id: str) -> str:
    """Enqueue on-demand task generation. Returns job_id."""
    job_id = str(uuid.uuid4())
    set_job_status(job_id, "pending")

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, run_task_generation_sync, project_id, user_id, job_id)
    except RuntimeError:
        _spawn_background(run_task_generation_sync, project_id, user_id, job_id)

    return job_id


# ---- Arq WorkerSettings (for `arq app.workers.arq_worker.WorkerSettings`) ----

class WorkerSettings:
    functions: ClassVar[list[Any]] = [arq_run_ingest, arq_run_audit]
    redis_settings = RedisSettings(
        host=get_settings().redis_url.split("://")[-1].split(":")[0] if "://" in get_settings().redis_url else "localhost",
        port=int(get_settings().redis_url.split(":")[-1]) if ":" in get_settings().redis_url and get_settings().redis_url.split(":")[-1].isdigit() else 6379,
    )
