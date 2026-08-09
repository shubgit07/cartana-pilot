"""Add pgvector HNSW index on Chunk.embedding for fast approximate similarity search.

Without an index every chat query scans all chunk vectors (O(n)). HNSW turns
that into a near-log lookup. Created in Phase 1 because the schema is fresh and
real embeddings land in the same phase.

Revision ID: 0002_hnsw_chunk_embedding
Revises: 0001_initial_schema
Create Date: 2026-08-06
"""
from __future__ import annotations

from alembic import op

revision = "0002_hnsw_chunk_embedding"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        'CREATE INDEX "Chunk_embedding_hnsw_idx" '
        'ON "Chunk" USING hnsw (embedding vector_cosine_ops)'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS "Chunk_embedding_hnsw_idx"')
