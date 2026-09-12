"""Pydantic schemas for the Sources module.

Field names are camelCase on purpose: these DTOs mirror ``SourceSummary`` and
``JobStatusView`` in ``packages/shared/src/types.ts``, which the Next.js
frontend already parses. Timestamps are ISO 8601 strings, never datetimes.

The input schema mirrors ``CreateSourceFromTextSchema`` in
``packages/shared/src/schemas.ts``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.core.serialization import enum_value, to_iso8601

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.db.models import Source

SourceKindLiteral = Literal["pdf", "text"]
SourceStatusLiteral = Literal["uploaded", "processing", "processed", "failed"]
SourceStageLiteral = Literal["uploading", "chunking", "ready", "failed"]


def _derive_stage(source: Source, chunks_total: int) -> SourceStageLiteral:
    """Map the coarse status onto a finer UI stage.

    Derived (no migration): "processing" with no chunks yet is still
    uploading; once chunks exist the pipeline is chunking/embedding/extracting.
    """
    status = enum_value(source.status)
    if status == "processed":
        return "ready"
    if status == "failed":
        return "failed"
    if status == "uploaded":
        return "uploading"
    return "chunking" if chunks_total > 0 else "uploading"


# ---- Response DTOs ----


class SourceSummary(BaseModel):
    """Mirrors ``SourceSummary`` in packages/shared/src/types.ts."""

    id: str
    projectId: str
    filename: str
    kind: SourceKindLiteral
    status: SourceStatusLiteral
    errorMessage: str | None = None
    createdAt: str
    chunkCount: int

    @classmethod
    def from_model(cls, source: Source, chunk_count: int) -> SourceSummary:
        return cls(
            id=source.id,
            projectId=source.project_id,
            filename=source.filename,
            kind=cast(SourceKindLiteral, enum_value(source.kind)),
            status=cast(SourceStatusLiteral, enum_value(source.status)),
            errorMessage=source.error_message,
            createdAt=to_iso8601(source.created_at),
            chunkCount=chunk_count,
        )


class JobStatusView(BaseModel):
    """Mirrors ``JobStatusView``: ingestion progress for a single source."""

    sourceId: str
    status: SourceStatusLiteral
    stage: SourceStageLiteral
    chunksTotal: int
    embedded: int
    errorMessage: str | None = None

    @classmethod
    def from_model(cls, source: Source, chunks_total: int, embedded: int) -> JobStatusView:
        return cls(
            sourceId=source.id,
            status=cast(SourceStatusLiteral, enum_value(source.status)),
            stage=_derive_stage(source, chunks_total),
            chunksTotal=chunks_total,
            embedded=embedded,
            errorMessage=source.error_message,
        )


# ---- Response envelopes ----


class SourceListResponse(BaseModel):
    sources: list[SourceSummary]


class SourceResponse(BaseModel):
    source: SourceSummary


class JobStatusResponse(BaseModel):
    status: JobStatusView


# ---- Input schemas ----


class CreateSourceFromText(BaseModel):
    """Mirrors ``CreateSourceFromTextSchema``: pasted text becomes a source."""

    # Zod objects strip unknown keys rather than rejecting them.
    model_config = ConfigDict(extra="ignore")

    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class CreateSourceFromDiff(BaseModel):
    """Payload for submitting raw Git Diffs or GitHub PR URLs."""

    model_config = ConfigDict(extra="ignore")

    filename: str = Field(default="implementation.diff", max_length=255)
    diffContent: str | None = Field(default=None, max_length=500000)
    githubPrUrl: str | None = Field(default=None, max_length=1000)

