"""Pydantic schemas for the Tasks module.

Mirrors ``TaskSummary``, ``TaskDetail`` in ``packages/shared/src/types.ts``
and ``CreateTaskSchema`` / ``UpdateTaskSchema`` in
``packages/shared/src/schemas.ts``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.requirement import ChunkLink, SourceLink
from app.core.serialization import enum_value, to_iso8601

if TYPE_CHECKING:
    from app.db.models import Task

TaskOriginLiteral = Literal["ai", "user"]
TaskStateLiteral = Literal["suggested", "accepted", "rejected", "edited"]


class TaskSummary(BaseModel):
    id: str
    projectId: str
    requirementId: str | None = None
    requirementTitle: str | None = None
    title: str
    description: str | None = None
    origin: TaskOriginLiteral
    state: TaskStateLiteral
    sourceLinks: list[SourceLink]
    createdAt: str
    updatedAt: str

    @classmethod
    def from_model(cls, task: Task, source_links: list[SourceLink]) -> TaskSummary:
        return cls(
            id=task.id,
            projectId=task.project_id,
            requirementId=task.requirement_id,
            requirementTitle=task.requirement.title if task.requirement else None,
            title=task.title,
            description=task.description,
            origin=enum_value(task.origin),
            state=enum_value(task.state),
            sourceLinks=source_links,
            createdAt=to_iso8601(task.created_at),
            updatedAt=to_iso8601(task.updated_at),
        )


class TaskDetail(TaskSummary):
    chunkLinks: list[ChunkLink]


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]


class TaskResponse(BaseModel):
    task: TaskSummary


class TaskGenerateResponse(BaseModel):
    jobId: str
    status: str


class TaskGenerateStatusResponse(BaseModel):
    jobId: str
    state: str
    result: object | None = None


class TaskDetailResponse(BaseModel):
    task: TaskDetail


class CreateTask(BaseModel):
    """Mirrors ``CreateTaskSchema``."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    requirementId: str | None = None


class UpdateTask(BaseModel):
    """Mirrors ``UpdateTaskSchema``."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    state: TaskStateLiteral | None = None
    requirementId: str | None = None
