"""SQLAlchemy ORM mapping for the existing Cartana PostgreSQL schema.

Table, column, enum, index, and foreign-key names deliberately match the
Prisma migration in ``apps/api/prisma/migrations``. This permits a gradual
backend cutover without changing the database consumed by the frontend.
"""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    """Create an opaque string identifier for new Python-created records.

    Existing Node records use CUIDs. IDs are opaque in the API and stored in
    TEXT columns, so UUID4 hex values remain schema- and contract-compatible
    while avoiding a runtime dependency solely for identifier formatting.
    """
    return uuid4().hex


class SourceKind(str, enum.Enum):
    PDF = "pdf"
    TEXT = "text"


class SourceStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class RequirementOrigin(str, enum.Enum):
    AI = "ai"
    USER = "user"


class RequirementState(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class TaskOrigin(str, enum.Enum):
    AI = "ai"
    USER = "user"


class TaskState(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class CoverageStatus(str, enum.Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    UNCLEAR = "unclear"
    MISSING = "missing"


class CoverageOrigin(str, enum.Enum):
    AI_SUGGESTED = "ai_suggested"
    USER_CONFIRMED = "user_confirmed"


class AuditSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditFindingKind(str, enum.Enum):
    UNCOVERED_REQUIREMENT = "uncovered_requirement"
    PARTIAL_COVERAGE = "partial_coverage"
    VAGUE_REQUIREMENT = "vague_requirement"
    DEADLINE_RISK = "deadline_risk"
    ORPHAN_TASK = "orphan_task"
    OTHER = "other"


def pgenum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Production-ready PostgreSQL Enum mapper ensuring lower-case wire values."""
    return Enum(enum_cls, name=name, values_callable=lambda obj: [item.value for item in obj])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    name: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=False), default=func.now(), onupdate=func.now(), nullable=False
    )

    projects: Mapped[list[Project]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sources: Mapped[list[Source]] = relationship(back_populates="user", cascade="all, delete-orphan")
    requirements: Mapped[list[Requirement]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship(back_populates="user", cascade="all, delete-orphan")
    coverage_links: Mapped[list[CoverageLink]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_runs: Mapped[list[AuditRun]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(TimestampMixin, Base):
    __tablename__ = "Project"
    __table_args__ = (Index("Project_userId_idx", "userId"), Index("Project_createdAt_idx", "createdAt"))

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="projects")
    sources: Mapped[list[Source]] = relationship(back_populates="project", cascade="all, delete-orphan")
    requirements: Mapped[list[Requirement]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship(back_populates="project", cascade="all, delete-orphan")
    coverage_links: Mapped[list[CoverageLink]] = relationship(back_populates="project", cascade="all, delete-orphan")
    audit_runs: Mapped[list[AuditRun]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Source(TimestampMixin, Base):
    __tablename__ = "Source"
    __table_args__ = (
        Index("Source_projectId_idx", "projectId"), Index("Source_userId_idx", "userId"), Index("Source_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[SourceKind] = mapped_column(pgenum(SourceKind, "SourceKind"), nullable=False)
    status: Mapped[SourceStatus] = mapped_column(pgenum(SourceStatus, "SourceStatus"), default=SourceStatus.UPLOADED, nullable=False)
    storage_key: Mapped[str] = mapped_column("storageKey", String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column("mimeType", String)
    size_bytes: Mapped[int | None] = mapped_column("sizeBytes", Integer)
    error_message: Mapped[str | None] = mapped_column("errorMessage", Text)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="sources")
    user: Mapped[User] = relationship(back_populates="sources")
    chunks: Mapped[list[Chunk]] = relationship(back_populates="source", cascade="all, delete-orphan")


class Chunk(TimestampMixin, Base):
    __tablename__ = "Chunk"
    __table_args__ = (Index("Chunk_sourceId_idx", "sourceId"), Index("Chunk_position_idx", "position"))

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column("sourceId", ForeignKey("Source.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))

    source: Mapped[Source] = relationship(back_populates="chunks")
    requirement_chunks: Mapped[list[RequirementChunk]] = relationship(back_populates="chunk", cascade="all, delete-orphan")
    task_chunks: Mapped[list[TaskChunk]] = relationship(back_populates="chunk", cascade="all, delete-orphan")


class Requirement(TimestampMixin, Base):
    __tablename__ = "Requirement"
    __table_args__ = (
        Index("Requirement_projectId_idx", "projectId"), Index("Requirement_userId_idx", "userId"),
        Index("Requirement_state_idx", "state"), Index("Requirement_dedupeKey_idx", "dedupeKey"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[RequirementOrigin] = mapped_column(pgenum(RequirementOrigin, "RequirementOrigin"), default=RequirementOrigin.AI, nullable=False)
    state: Mapped[RequirementState] = mapped_column(pgenum(RequirementState, "RequirementState"), default=RequirementState.SUGGESTED, nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column("dedupeKey", String)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="requirements")
    user: Mapped[User] = relationship(back_populates="requirements")
    chunks: Mapped[list[RequirementChunk]] = relationship(back_populates="requirement", cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship(back_populates="requirement")
    coverage_links: Mapped[list[CoverageLink]] = relationship(back_populates="requirement", cascade="all, delete-orphan")
    findings: Mapped[list[AuditFinding]] = relationship(back_populates="requirement")


class RequirementChunk(Base):
    __tablename__ = "RequirementChunk"
    __table_args__ = (Index("RequirementChunk_chunkId_idx", "chunkId"),)

    requirement_id: Mapped[str] = mapped_column("requirementId", ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    chunk_id: Mapped[str] = mapped_column("chunkId", ForeignKey("Chunk.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

    requirement: Mapped[Requirement] = relationship(back_populates="chunks")
    chunk: Mapped[Chunk] = relationship(back_populates="requirement_chunks")


class Task(TimestampMixin, Base):
    __tablename__ = "Task"
    __table_args__ = (
        Index("Task_projectId_idx", "projectId"), Index("Task_userId_idx", "userId"), Index("Task_requirementId_idx", "requirementId"),
        Index("Task_state_idx", "state"), Index("Task_dedupeKey_idx", "dedupeKey"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    requirement_id: Mapped[str | None] = mapped_column("requirementId", ForeignKey("Requirement.id", ondelete="SET NULL", onupdate="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[TaskOrigin] = mapped_column(pgenum(TaskOrigin, "TaskOrigin"), default=TaskOrigin.AI, nullable=False)
    state: Mapped[TaskState] = mapped_column(pgenum(TaskState, "TaskState"), default=TaskState.SUGGESTED, nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column("dedupeKey", String)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="tasks")
    user: Mapped[User] = relationship(back_populates="tasks")
    requirement: Mapped[Requirement | None] = relationship(back_populates="tasks")
    chunks: Mapped[list[TaskChunk]] = relationship(back_populates="task", cascade="all, delete-orphan")
    coverage_links: Mapped[list[CoverageLink]] = relationship(back_populates="task", cascade="all, delete-orphan")
    findings: Mapped[list[AuditFinding]] = relationship(back_populates="task")


class TaskChunk(Base):
    __tablename__ = "TaskChunk"
    __table_args__ = (Index("TaskChunk_chunkId_idx", "chunkId"),)

    task_id: Mapped[str] = mapped_column("taskId", ForeignKey("Task.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    chunk_id: Mapped[str] = mapped_column("chunkId", ForeignKey("Chunk.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

    task: Mapped[Task] = relationship(back_populates="chunks")
    chunk: Mapped[Chunk] = relationship(back_populates="task_chunks")


class CoverageLink(TimestampMixin, Base):
    __tablename__ = "CoverageLink"
    __table_args__ = (
        UniqueConstraint("requirementId", "taskId", name="CoverageLink_requirementId_taskId_key"),
        Index("CoverageLink_projectId_idx", "projectId"), Index("CoverageLink_requirementId_idx", "requirementId"), Index("CoverageLink_taskId_idx", "taskId"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    requirement_id: Mapped[str] = mapped_column("requirementId", ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    task_id: Mapped[str] = mapped_column("taskId", ForeignKey("Task.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    status: Mapped[CoverageStatus] = mapped_column(pgenum(CoverageStatus, "CoverageStatus"), nullable=False)
    origin: Mapped[CoverageOrigin] = mapped_column(pgenum(CoverageOrigin, "CoverageOrigin"), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="coverage_links")
    user: Mapped[User] = relationship(back_populates="coverage_links")
    requirement: Mapped[Requirement] = relationship(back_populates="coverage_links")
    task: Mapped[Task] = relationship(back_populates="coverage_links")


class AuditRun(TimestampMixin, Base):
    __tablename__ = "AuditRun"
    __table_args__ = (Index("AuditRun_projectId_idx", "projectId"), Index("AuditRun_createdAt_idx", "createdAt"))

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="audit_runs")
    user: Mapped[User] = relationship(back_populates="audit_runs")
    findings: Mapped[list[AuditFinding]] = relationship(back_populates="run", cascade="all, delete-orphan")


class AuditFinding(TimestampMixin, Base):
    __tablename__ = "AuditFinding"
    __table_args__ = (Index("AuditFinding_runId_idx", "runId"), Index("AuditFinding_projectId_idx", "projectId"), Index("AuditFinding_severity_idx", "severity"))

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column("runId", ForeignKey("AuditRun.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", String, nullable=False)
    kind: Mapped[AuditFindingKind] = mapped_column(pgenum(AuditFindingKind, "AuditFindingKind"), nullable=False)
    severity: Mapped[AuditSeverity] = mapped_column(pgenum(AuditSeverity, "AuditSeverity"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_id: Mapped[str | None] = mapped_column("requirementId", ForeignKey("Requirement.id", ondelete="SET NULL", onupdate="CASCADE"))
    task_id: Mapped[str | None] = mapped_column("taskId", ForeignKey("Task.id", ondelete="SET NULL", onupdate="CASCADE"))

    run: Mapped[AuditRun] = relationship(back_populates="findings")
    requirement: Mapped[Requirement | None] = relationship(back_populates="findings")
    task: Mapped[Task | None] = relationship(back_populates="findings")
