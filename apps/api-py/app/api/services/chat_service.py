"""Chat module — retrieval + generation.

Port of ``apps/api/src/modules/chat/service.ts`` + ``retrieval.ts``.

RAG flow: embed the question → pgvector cosine similarity search → AI generation
with citations. All scoped by user_id + project_id.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas.chat import ChatAsk, ChatCitation, ChatMessage, ChatResponse
from app.api.services.project_service import get_owned_project
from app.core.errors import NotFoundError
from app.providers.ai_provider import AIChatInput, ChatPassage, get_ai_provider
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
    """Verify ownership, retrieve passages, generate answer with citations."""
    get_owned_project(db, user_id, project_id)

    passages = retrieve_passages(db, user_id, project_id, payload.question)

    ai = get_ai_provider()
    history = []
    if payload.history:
        history = [{"role": m.role, "content": m.content} for m in payload.history]

    out = ai.chat(AIChatInput(
        question=payload.question,
        history=history,
        passages=passages,
    ))

    message = ChatMessage(
        role="assistant",
        content=out.answer,
        citations=out.citations,
        createdAt=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    return ChatResponse(message=message)
