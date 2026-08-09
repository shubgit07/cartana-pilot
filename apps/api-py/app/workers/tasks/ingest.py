"""Ingest pipeline module re-exports.

Re-exports enqueue helpers and status checks from `app.workers.arq_worker`,
which is backed by Arq (Asyncio Redis Queue).
"""
from app.workers.arq_worker import (
    enqueue_audit,
    enqueue_ingest,
    enqueue_task_generation,
    get_job_status,
)
from app.workers.arq_worker import (
    execute_chunk_stage as run_chunk,
)
from app.workers.arq_worker import (
    execute_embed_stage as run_embed,
)
from app.workers.arq_worker import (
    execute_extract_requirements_stage as run_extract_requirements,
)
from app.workers.arq_worker import (
    execute_extract_tasks_stage as run_extract_tasks,
)
from app.workers.arq_worker import (
    execute_ingest_stage as run_ingest,
)
from app.workers.arq_worker import (
    run_audit_sync as run_audit_task,
)

__all__ = [
    "enqueue_audit",
    "enqueue_ingest",
    "enqueue_task_generation",
    "get_job_status",
    "run_audit_task",
    "run_chunk",
    "run_embed",
    "run_extract_requirements",
    "run_extract_tasks",
    "run_ingest",
]
