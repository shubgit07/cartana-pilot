"""Chat module.

Port of ``apps/api/src/modules/chat/service.ts`` + ``retrieval.ts``.

The user-facing chat endpoint is intentionally **not wired up** yet: no LLM is
configured for the chat role, so requests are rejected with HTTP 501. The
``retrieve_passages`` helper (pgvector cosine similarity search) remains in
place for the future RAG implementation.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas.chat import ChatAsk, ChatResponse
from app.api.services.project_service import get_owned_project
from app.core.errors import AppError
from app.providers.ai_provider import ChatPassage
from app.providers.embedding_provider import get_embedding_provider, to_pg_vector_literal

logger = logging.getLogger(__name__)


def retrieve_passages(
    db: Session,
    user_id: str,
    project_id: str,
    question: str,
    top_k: int = 6,
) -> list[ChatPassage]:
    """pgvector cosine similarity search over Chunks scoped to a project."""
    dialect = db.get_bind().dialect.name
    if dialect != "postgresql":
        logger.info("pgvector retrieval requires Postgres; skipping (dialect=%s)", dialect)
        return []

    provider = get_embedding_provider()
    vectors = provider.embed([question])
    if not vectors:
        return []

    vec = vectors[0]
    lit = to_pg_vector_literal(vec)

    sql = text("""
        SELECT
          c.id          AS "id",
          c."sourceId"  AS "sourceId",
          c.text        AS "text",
          s.filename    AS "filename",
          1 - (c.embedding <=> :vec::vector) AS "score"
        FROM "Chunk" c
        JOIN "Source" s ON s.id = c."sourceId"
        WHERE c.embedding IS NOT NULL
          AND s."projectId" = :project_id
          AND s."userId" = :user_id
        ORDER BY c.embedding <=> :vec::vector
        LIMIT :top_k
    """)

    rows = db.execute(sql, {
        "vec": lit,
        "project_id": project_id,
        "user_id": user_id,
        "top_k": top_k,
    }).all()

    return [
        ChatPassage(
            chunkId=row.id,
            sourceId=row.sourceId,
            filename=row.filename,
            text=row.text,
            score=float(row.score),
        )
        for row in rows
    ]


def ask_project(
    db: Session, user_id: str, project_id: str, payload: ChatAsk
) -> ChatResponse:
    """Chat is intentionally not wired up — reject with a clear error.

    No LLM is configured for the chat role, so every request returns HTTP 501
    instead of falling back to retrieval-only answers. Ownership is still
    verified so a missing project reports a correct 404. Enable retrieval and
    generation here once a chat LLM provider is wired up.
    """
    get_owned_project(db, user_id, project_id)

    raise AppError(
        "LLM is not wired up",
        status_code=501,
        code="chat_not_wired",
    )
