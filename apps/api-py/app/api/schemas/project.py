"""Pydantic schemas for the Projects module.

Field names are intentionally camelCase: the Next.js frontend already parses
the DTOs produced by the Node backend (see ProjectSummary / ProjectDetail in
``packages/shared/src/types.ts``), so the JSON shape must be identical - no
extra fields, no renames, and dates as ISO 8601 strings rather than datetime
objects.

Input schemas mirror the Zod schemas in ``packages/shared/src/schemas.ts``
(CreateProjectSchema / UpdateProjectSchema), including their length limits.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.source import SourceSummary
from app.core.serialization import to_iso8601

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.db.models import Project

__all__ = [
    "CreateProject",
    "ProjectDetail",
    "ProjectDetailResponse",
    "ProjectListResponse",
    "ProjectResponse",
    "ProjectSummary",
    "SourceSummary",
    "UpdateProject",
]


# ---- Response DTOs ----


class ProjectSummary(BaseModel):
    """Mirrors ``ProjectSummary`` in packages/shared/src/types.ts."""

    id: str
    name: str
    description: str | None = None
    createdAt: str
    sourceCount: int

    @classmethod
    def from_model(cls, project: Project, source_count: int) -> ProjectSummary:
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            createdAt=to_iso8601(project.created_at),
            sourceCount=source_count,
        )


class ProjectDetail(ProjectSummary):
    """Mirrors ``ProjectDetail``: a summary plus its sources."""

    sources: list[SourceSummary]

    @classmethod
    def from_project(cls, project: Project, sources: list[SourceSummary]) -> ProjectDetail:
        summary = ProjectSummary.from_model(project, source_count=len(sources))
        return cls(**summary.model_dump(), sources=sources)


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
    description: str | None = Field(default=None, max_length=2000)


class UpdateProject(BaseModel):
    """Mirrors ``UpdateProjectSchema``: both fields optional.

    Omitted fields are left untouched by the service (it inspects the set of
    provided fields), while an explicit ``"description": null`` clears the
    stored value - the same distinction the Node service makes with
    ``input.description !== undefined``.
    """

    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
