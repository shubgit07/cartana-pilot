"""Pydantic schemas for the Requirements module.

Mirrors ``RequirementSummary``, ``RequirementDetail`` in
``packages/shared/src/types.ts`` and ``UpdateRequirementSchema`` in
``packages/shared/src/schemas.ts``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.core.serialization import enum_value, to_iso8601

if TYPE_CHECKING:
    from app.db.models import Requirement

RequirementOriginLiteral = Literal["ai", "user"]
RequirementStateLiteral = Literal["suggested", "accepted", "rejected", "edited"]


class SourceLink(BaseModel):
    sourceId: str
    filename: str


class ChunkLink(BaseModel):
    chunkId: str
    sourceId: str
    filename: str
    snippet: str


class RequirementSummary(BaseModel):
    id: str
    projectId: str
    title: str
    description: str | None = None
    origin: RequirementOriginLiteral
    state: RequirementStateLiteral
    sourceLinks: list[SourceLink]
    createdAt: str
    updatedAt: str

    @classmethod
    def from_model(cls, req: Requirement, source_links: list[SourceLink]) -> RequirementSummary:
        return cls(
            id=req.id,
            projectId=req.project_id,
            title=req.title,
            description=req.description,
            origin=cast(RequirementOriginLiteral, enum_value(req.origin)),
            state=cast(RequirementStateLiteral, enum_value(req.state)),
            sourceLinks=source_links,
            createdAt=to_iso8601(req.created_at),
            updatedAt=to_iso8601(req.updated_at),
        )


class RequirementDetail(RequirementSummary):
    chunkLinks: list[ChunkLink]


class RequirementListResponse(BaseModel):
    requirements: list[RequirementSummary]


class RequirementResponse(BaseModel):
    requirement: RequirementSummary


class RequirementDetailResponse(BaseModel):
    requirement: RequirementDetail


class UpdateRequirement(BaseModel):
    """Mirrors ``UpdateRequirementSchema``."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    state: RequirementStateLiteral | None = None
