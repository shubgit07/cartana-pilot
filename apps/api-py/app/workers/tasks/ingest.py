"""Ingest pipeline module re-exports.

Re-exports enqueue helpers and status checks from `app.workers.arq_worker`.
This completely replaces Celery with ARQ.
"""
from app.workers.arq_worker import (
    enqueue_audit,
    enqueue_ingest,
    execute_chunk_stage as run_chunk,
    execute_embed_stage as run_embed,
    execute_extract_requirements_stage as run_extract_requirements,
    execute_extract_tasks_stage as run_extract_tasks,
    execute_ingest_stage as run_ingest,
    get_job_status,
    run_audit_sync as run_audit_task,
)

__all__ = [
    "enqueue_ingest",
    "enqueue_audit",
    "get_job_status",
    "run_ingest",
    "run_chunk",
    "run_embed",
    "run_extract_requirements",
    "run_extract_tasks",
    "run_audit_task",
]
