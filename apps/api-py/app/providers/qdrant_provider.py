"""Qdrant vector store for repository code chunks.

Qdrant is the primary vector index for Cartana: Postgres (Neon) remains the
source of truth for files, chunks, snapshots, and verdicts, while Qdrant
holds ``{id, vector, payload}`` mirrors used for semantic retrieval.

Design notes:
- Point id == ``CodeChunk.id`` (opaque string) so the DB row and the point
  are trivially joinable by id. Re-syncs upsert the same ids: idempotent.
- Payload carries everything the verifier needs without a DB round-trip:
  ``projectId`` (isolation filter), ``kind`` (``code`` today, ``doc`` later),
  ``path``, ``startLine``, ``endLine``, and ``content``.
- All Qdrant I/O is best-effort at the call site: indexing and verification
  must succeed (diff-only / keyword fallback) when Qdrant is unreachable.
- ``get_code_index()`` returns None when Qdrant is not configured, so local
  dev and tests run without any vector service.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import get_settings
from app.db.models import CodeChunk

logger = logging.getLogger(__name__)

VECTOR_SIZE = 768


@dataclass
class CodePoint:
    """One chunk to upsert: id matches the Postgres CodeChunk row."""

    id: str
    vector: list[float]
    project_id: str
    path: str
    start_line: int
    end_line: int
    content: str
    kind: str = "code"


@dataclass
class QdrantHit:
    """One scored retrieval result (cosine similarity, higher is better)."""

    path: str
    start_line: int
    end_line: int
    content: str
    score: float


@dataclass
class QdrantCodeIndex:
    url: str
    api_key: str | None = None
    collection: str = "cartana_code_chunks"
    dim: int = VECTOR_SIZE
    timeout_seconds: float = 20.0

    def _client(self):  # type: ignore[no-untyped-def]
        from qdrant_client import QdrantClient

        return QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            # Skip the constructor version probe: serverless wake-ups make it
            # slow/flaky, and sync/search degrade gracefully without it.
            check_compatibility=False,
        )

    def ensure_collection(self) -> None:
        """Create the collection on first use; no-op when it exists."""
        from qdrant_client.http.models import Distance, VectorParams

        client = self._client()
        try:
            if client.collection_exists(self.collection):
                return
            client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )
            logger.info("Qdrant collection %r created (dim=%d).", self.collection, self.dim)
        finally:
            client.close()

    def upsert_chunks(self, points: list[CodePoint]) -> int:
        """Upsert chunk points (idempotent by CodeChunk id). Returns count."""
        from qdrant_client.http.models import PointStruct

        if not points:
            return 0
        client = self._client()
        try:
            client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=p.id,
                        vector=p.vector,
                        payload={
                            "projectId": p.project_id,
                            "kind": p.kind,
                            "path": p.path,
                            "startLine": p.start_line,
                            "endLine": p.end_line,
                            "content": p.content,
                        },
                    )
                    for p in points
                ],
            )
            return len(points)
        finally:
            client.close()

    def search(
        self, *, project_id: str, vector: list[float], top_k: int = 3
    ) -> list[QdrantHit]:
        """Cosine search scoped to one project via payload filter."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        client = self._client()
        try:
            result = client.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=Filter(
                    must=[FieldCondition(key="projectId", match=MatchValue(value=project_id))]
                ),
                limit=top_k,
                with_payload=True,
            )
            hits: list[QdrantHit] = []
            for point in result.points:
                payload = point.payload or {}
                content = payload.get("content", "")
                if not content:
                    continue
                hits.append(QdrantHit(
                    path=str(payload.get("path", "")),
                    start_line=int(payload.get("startLine", 1)),
                    end_line=int(payload.get("endLine", 1)),
                    content=str(content),
                    score=float(point.score),
                ))
            return hits
        finally:
            client.close()

    def delete_by_project(self, project_id: str) -> None:
        """Delete every point whose payload ``projectId`` matches. Idempotent."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        client = self._client()
        try:
            client.delete(
                collection_name=self.collection,
                points_selector=Filter(
                    must=[FieldCondition(key="projectId", match=MatchValue(value=project_id))]
                ),
            )
            logger.info("Qdrant points deleted (project_id=%s).", project_id)
        finally:
            client.close()


def get_code_index() -> QdrantCodeIndex | None:
    """Return the configured Qdrant code index, or None when not configured."""
    settings = get_settings()
    if not settings.qdrant_url:
        return None
    dim = settings.embedding_dim or VECTOR_SIZE
    return QdrantCodeIndex(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection_name or "cartana_code_chunks",
        dim=dim,
    )


def build_code_points(
    items: list[tuple[CodeChunk, str]], *, project_id: str, kind: str = "code"
) -> list[CodePoint]:
    """Map ``(CodeChunk row, file path)`` pairs to Qdrant points.

    Rows without vectors are skipped (embedding failures still leave a
    usable Postgres row for keyword fallback and audit).
    """
    points: list[CodePoint] = []
    for chunk, path in items:
        vector = chunk.embedding
        # NOTE: pgvector returns numpy arrays on some dialects, where
        # truthiness is ambiguous — check length instead of truth value.
        if vector is None or len(vector) == 0:
            continue
        points.append(CodePoint(
            id=chunk.id,
            vector=list(vector),
            project_id=project_id,
            path=path,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content=chunk.content,
            kind=kind,
        ))
    return points
