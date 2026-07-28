"""Ingest task.

Stub stage of the ingest -> chunk -> embed -> extract pipeline: it only moves
the source through the ``processing`` and ``processed`` states so the status
endpoint and the frontend polling behave like the Node backend. The real work
(text extraction, chunking, embedding) lands in a later migration step.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import Source, SourceStatus
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

INGEST_TASK_NAME = "sources.ingest"


@celery_app.task(name=INGEST_TASK_NAME)
def run_ingest(
    source_id: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Mark a source as processing, then processed."""
    logger.info("ingest not yet implemented (source_id=%s, project_id=%s)", source_id, project_id)

    session = SessionLocal()
    try:
        source = session.get(Source, source_id)
        if source is None:
            logger.warning("ingest skipped, source no longer exists (source_id=%s)", source_id)
            return {"sourceId": source_id, "status": None}

        source.status = SourceStatus.PROCESSING
        session.commit()

        # The chunk -> embed -> extract pipeline will run here.

        source.status = SourceStatus.PROCESSED
        source.error_message = None
        session.commit()
        return {"sourceId": source_id, "status": SourceStatus.PROCESSED.value}
    except Exception as exc:  # noqa: BLE001 - the failure is recorded on the row
        session.rollback()
        logger.exception("ingest failed (source_id=%s)", source_id)
        _mark_failed(session, source_id, str(exc))
        raise
    finally:
        session.close()


def _mark_failed(session: Session, source_id: str, message: str) -> None:
    try:
        source = session.get(Source, source_id)
        if source is not None:
            source.status = SourceStatus.FAILED
            source.error_message = message
            session.commit()
    except Exception:  # noqa: BLE001 - never mask the original failure
        session.rollback()
        logger.exception("could not record ingest failure (source_id=%s)", source_id)


def enqueue_ingest(source_id: str, project_id: str, user_id: str) -> None:
    """Queue ingestion for a source.

    A broker outage must not fail the upload request: the row is already
    persisted with status ``uploaded`` and can be re-queued later, so the
    failure is logged rather than raised.
    """
    try:
        run_ingest.apply_async(
            kwargs={"source_id": source_id, "project_id": project_id, "user_id": user_id},
            task_id=f"ingest-{source_id}",
        )
    except Exception:  # noqa: BLE001 - queueing is best effort
        logger.exception("could not enqueue ingest job (source_id=%s)", source_id)
