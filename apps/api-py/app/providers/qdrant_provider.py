"""Qdrant Cloud Vector Database Provider.

Provides a clean interface to Qdrant Cloud (or local Qdrant memory fallback) for storing
and searching vector embeddings with 768-dimension COSINE similarity distance.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class QdrantChunkPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any]


class QdrantProvider:
    """Wrapper for Qdrant Cloud client interactions."""

    def __init__(self, url: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self._url = url or settings.qdrant_url
        self._api_key = api_key or settings.qdrant_api_key
        self._collection_name = settings.qdrant_collection_name
        self._dim = settings.embedding_dim
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client package is required. Install with: pip install qdrant-client"
            ) from exc

        if self._url and self._api_key:
            logger.info("Initializing Qdrant Cloud client at %s", self._url)
            self._client = QdrantClient(url=self._url, api_key=self._api_key, timeout=30)
        else:
            logger.warning("QDRANT_URL or QDRANT_API_KEY missing — using in-memory Qdrant client")
            self._client = QdrantClient(location=":memory:")

        self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        from qdrant_client.http import models

        try:
            collections = [c.name for c in self._client.get_collections().collections]
            if self._collection_name not in collections:
                logger.info("Creating Qdrant collection: %s (dim=%d)", self._collection_name, self._dim)
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=models.VectorParams(
                        size=self._dim,
                        distance=models.Distance.COSINE,
                    ),
                )
        except Exception as exc:
            logger.error("Failed to check/create Qdrant collection %s: %s", self._collection_name, exc)
            raise

    def upsert_chunks(self, points: list[QdrantChunkPoint]) -> int:
        """Upsert a list of vector chunk points into Qdrant Cloud."""
        if not points:
            return 0

        from qdrant_client.http import models

        client = self._get_client()
        qpoints = [
            models.PointStruct(
                id=p.id,
                vector=p.vector,
                payload=p.payload,
            )
            for p in points
        ]

        client.upsert(
            collection_name=self._collection_name,
            points=qpoints,
            wait=True,
        )
        logger.info("Upserted %d vector points to Qdrant collection %s", len(points), self._collection_name)
        return len(points)

    def search_similar(
        self, query_vector: list[float], limit: int = 5, filter_payload: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search for top-K similar vector chunks in Qdrant."""
        client = self._get_client()
        from qdrant_client.http import models

        query_filter = None
        if filter_payload:
            must_conditions = [
                models.FieldCondition(
                    key=k,
                    match=models.MatchValue(value=v),
                )
                for k, v in filter_payload.items()
            ]
            query_filter = models.Filter(must=must_conditions)

        results = client.search(
            collection_name=self._collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload or {},
            }
            for r in results
        ]


_qdrant_instance: QdrantProvider | None = None


def get_qdrant_provider() -> QdrantProvider:
    global _qdrant_instance
    if _qdrant_instance is None:
        _qdrant_instance = QdrantProvider()
    return _qdrant_instance
