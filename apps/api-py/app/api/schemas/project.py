"""Pydantic schemas for the Projects module.

Field names are intentionally camelCase: the Next.js frontend already parses
the DTOs produced by the Node backend (see ProjectSummary / ProjectDetail /
SourceSummary in ``packages/shared/src/types.ts``), so the JSON shape must be
identical - no extra fields, no renames, and dates as ISO 8601 strings rather
than datetime objects.

Input schemas mirror the Zod schemas in ``packages/shared/src/schemas.ts``
(CreateProjectSchema / UpdateProjectSchema), including their length limits.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SourceKindLiteral = Literal["pdf", "text"]
SourceStatusLiteral = Literal["uploaded", "processing", "processed", "failed"]


# ---- Response DTOs ----


class SourceSummary(BaseModel):
    """Mirrors ``SourceSummary`` in packages/shared/src/types.ts."""

    id: str
    projectId: str
    filename: str
    kind: SourceKindLiteral
    status: SourceStatusLiteral
    errorMessage: Optional[str] = None
    createdAt: str
    chunkCount: int


class ProjectSummary(BaseModel):
    """Mirrors ``ProjectSummary`` in packages/shared/src/types.ts."""

    id: str
    name: str
    description: Optional[str] = None
    createdAt: str
    sourceCount: int


class ProjectDetail(ProjectSummary):
    """Mirrors ``ProjectDetail``: a summary plus its sources."""

    sources: list[SourceSummary]


# ---- Response envelopes ----


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummary]


class ProjectResponse(BaseModel):
    project: ProjectSummary


class ProjectDetailResponse(BaseModel):
    project: ProjectDetail


# ---- Input schemas ----


class CreateProject(BaseModel):
    """Mirrors ``CreateProjectSchema``: name required, description optional."""

    # Zod objects strip unknown keys rather than rejecting them.
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)


class UpdateProject(BaseModel):
    """Mirrors ``UpdateProjectSchema``: both fields optional.

    Omitted fields are left untouched by the service (it inspects
    ``model_fields_set``), while an explicit ``"description": null`` clears the
    stored value - the same distinction the Node service makes with
    ``input.description !== undefined``.
    """

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
