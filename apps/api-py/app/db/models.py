"""SQLAlchemy ORM mapping for the existing Cartana PostgreSQL schema.

Table, column, enum, index, and foreign-key names deliberately match the
Prisma migration in ``apps/api/prisma/migrations``. This permits a gradual
backend cutover without changing the database consumed by the frontend.
"""
from __future__ import annotations

import enum
from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
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


class RepositoryProvider(str, enum.Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    GENERIC_GIT = "generic_git"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SnapshotKind(str, enum.Enum):
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"


class SymbolKind(str, enum.Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    INTERFACE = "interface"
    TYPE = "type"
    CONSTANT = "constant"
    OTHER = "other"


class VerificationVerdict(str, enum.Enum):
    SATISFIED = "satisfied"
    PARTIAL = "partial"
    NOT_SATISFIED = "not_satisfied"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class EvidenceKind(str, enum.Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXT = "context"


def pgenum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Production-ready PostgreSQL Enum mapper ensuring lower-case wire values."""
    return Enum(enum_cls, name=name, values_callable=lambda obj: [item.value for item in obj])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
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


class RequirementChunk(Base):
    __tablename__ = "RequirementChunk"
    __table_args__ = (Index("RequirementChunk_chunkId_idx", "chunkId"),)

    requirement_id: Mapped[str] = mapped_column("requirementId", ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    chunk_id: Mapped[str] = mapped_column("chunkId", ForeignKey("Chunk.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

    requirement: Mapped[Requirement] = relationship(back_populates="chunks")
    chunk: Mapped[Chunk] = relationship(back_populates="requirement_chunks")


class RepositoryConnection(TimestampMixin, Base):
    __tablename__ = "RepositoryConnection"
    __table_args__ = (
        UniqueConstraint("projectId", "provider", "externalId", name="RepositoryConnection_project_provider_external_key"),
        Index("RepositoryConnection_projectId_idx", "projectId"),
        Index("RepositoryConnection_userId_idx", "userId"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    provider: Mapped[RepositoryProvider] = mapped_column(pgenum(RepositoryProvider, "RepositoryProvider"), nullable=False)
    external_id: Mapped[str] = mapped_column("externalId", String, nullable=False)
    clone_url: Mapped[str] = mapped_column("cloneUrl", Text, nullable=False)
    default_branch: Mapped[str] = mapped_column("defaultBranch", String, nullable=False)
    display_name: Mapped[str] = mapped_column("displayName", String, nullable=False)
    is_active: Mapped[bool] = mapped_column("isActive", Boolean, default=True, server_default=text("true"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column("updatedAt", DateTime(), default=func.now(), onupdate=func.now(), nullable=False)

    snapshots: Mapped[list[RepositorySnapshot]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class RepositorySnapshot(TimestampMixin, Base):
    __tablename__ = "RepositorySnapshot"
    __table_args__ = (
        UniqueConstraint("repositoryId", "commitSha", name="RepositorySnapshot_repository_commit_key"),
        Index("RepositorySnapshot_projectId_idx", "projectId"),
        Index("RepositorySnapshot_repositoryId_idx", "repositoryId"),
        Index("RepositorySnapshot_commitSha_idx", "commitSha"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column("repositoryId", ForeignKey("RepositoryConnection.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    kind: Mapped[SnapshotKind] = mapped_column(pgenum(SnapshotKind, "SnapshotKind"), nullable=False)
    commit_sha: Mapped[str] = mapped_column("commitSha", String(64), nullable=False)
    tree_sha: Mapped[str | None] = mapped_column("treeSha", String(64))
    ref_name: Mapped[str | None] = mapped_column("refName", String)
    base_commit_sha: Mapped[str | None] = mapped_column("baseCommitSha", String(64))
    pull_request_number: Mapped[int | None] = mapped_column("pullRequestNumber", Integer)
    committed_at: Mapped[datetime | None] = mapped_column("committedAt", DateTime())
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)

    repository: Mapped[RepositoryConnection] = relationship(back_populates="snapshots")
    files: Mapped[list[RepositoryFile]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    index_runs: Mapped[list[IndexRun]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    verification_runs: Mapped[list[VerificationRun]] = relationship(back_populates="snapshot")


class RepositoryFile(TimestampMixin, Base):
    __tablename__ = "RepositoryFile"
    __table_args__ = (
        UniqueConstraint("snapshotId", "path", name="RepositoryFile_snapshot_path_key"),
        Index("RepositoryFile_projectId_idx", "projectId"),
        Index("RepositoryFile_snapshotId_idx", "snapshotId"),
        Index("RepositoryFile_blobSha_idx", "blobSha"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column("snapshotId", ForeignKey("RepositorySnapshot.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    blob_sha: Mapped[str] = mapped_column("blobSha", String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column("contentHash", String(64), nullable=False)
    language: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column("sizeBytes", Integer, nullable=False)
    line_count: Mapped[int | None] = mapped_column("lineCount", Integer)
    is_binary: Mapped[bool] = mapped_column("isBinary", Boolean, default=False, server_default=text("false"), nullable=False)

    snapshot: Mapped[RepositorySnapshot] = relationship(back_populates="files")
    symbols: Mapped[list[CodeSymbol]] = relationship(back_populates="file", cascade="all, delete-orphan")
    chunks: Mapped[list[CodeChunk]] = relationship(back_populates="file", cascade="all, delete-orphan")


class CodeSymbol(TimestampMixin, Base):
    __tablename__ = "CodeSymbol"
    __table_args__ = (
        UniqueConstraint("fileId", "qualifiedName", "startLine", name="CodeSymbol_file_name_line_key"),
        CheckConstraint('"startLine" > 0 AND "endLine" >= "startLine"', name="CodeSymbol_valid_lines_check"),
        Index("CodeSymbol_projectId_idx", "projectId"),
        Index("CodeSymbol_fileId_idx", "fileId"),
        Index("CodeSymbol_qualifiedName_idx", "qualifiedName"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column("fileId", ForeignKey("RepositoryFile.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    kind: Mapped[SymbolKind] = mapped_column(pgenum(SymbolKind, "SymbolKind"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    qualified_name: Mapped[str] = mapped_column("qualifiedName", Text, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text)
    start_line: Mapped[int] = mapped_column("startLine", Integer, nullable=False)
    end_line: Mapped[int] = mapped_column("endLine", Integer, nullable=False)
    symbol_hash: Mapped[str] = mapped_column("symbolHash", String(64), nullable=False)

    file: Mapped[RepositoryFile] = relationship(back_populates="symbols")


class IndexRun(TimestampMixin, Base):
    __tablename__ = "IndexRun"
    __table_args__ = (
        Index("IndexRun_projectId_idx", "projectId"),
        Index("IndexRun_snapshotId_idx", "snapshotId"),
        Index("IndexRun_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column("snapshotId", ForeignKey("RepositorySnapshot.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(pgenum(RunStatus, "RunStatus"), default=RunStatus.PENDING, nullable=False)
    index_version: Mapped[str] = mapped_column("indexVersion", String, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column("embeddingModel", String)
    embedding_dimension: Mapped[int] = mapped_column("embeddingDimension", Integer, default=768, server_default=text("768"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column("startedAt", DateTime())
    completed_at: Mapped[datetime | None] = mapped_column("completedAt", DateTime())
    error_message: Mapped[str | None] = mapped_column("errorMessage", Text)
    stats: Mapped[dict | None] = mapped_column(JSON)

    snapshot: Mapped[RepositorySnapshot] = relationship(back_populates="index_runs")
    chunks: Mapped[list[CodeChunk]] = relationship(back_populates="index_run", cascade="all, delete-orphan")


class CodeChunk(TimestampMixin, Base):
    __tablename__ = "CodeChunk"
    __table_args__ = (
        UniqueConstraint("indexRunId", "fileId", "ordinal", name="CodeChunk_run_file_ordinal_key"),
        CheckConstraint('"startLine" > 0 AND "endLine" >= "startLine"', name="CodeChunk_valid_lines_check"),
        Index("CodeChunk_projectId_idx", "projectId"),
        Index("CodeChunk_fileId_idx", "fileId"),
        Index("CodeChunk_indexRunId_idx", "indexRunId"),
        Index("CodeChunk_contentHash_idx", "contentHash"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    index_run_id: Mapped[str] = mapped_column("indexRunId", ForeignKey("IndexRun.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    file_id: Mapped[str] = mapped_column("fileId", ForeignKey("RepositoryFile.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column("startLine", Integer, nullable=False)
    end_line: Mapped[int] = mapped_column("endLine", Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column("contentHash", String(64), nullable=False)
    token_count: Mapped[int | None] = mapped_column("tokenCount", Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))

    index_run: Mapped[IndexRun] = relationship(back_populates="chunks")
    file: Mapped[RepositoryFile] = relationship(back_populates="chunks")
    evidence_references: Mapped[list[EvidenceReference]] = relationship(back_populates="chunk")


class RequirementRevision(TimestampMixin, Base):
    __tablename__ = "RequirementRevision"
    __table_args__ = (
        UniqueConstraint("requirementId", "revision", name="RequirementRevision_requirement_revision_key"),
        UniqueConstraint("requirementId", "contentHash", name="RequirementRevision_requirement_hash_key"),
        Index("RequirementRevision_projectId_idx", "projectId"),
        Index("RequirementRevision_requirementId_idx", "requirementId"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    requirement_id: Mapped[str] = mapped_column("requirementId", ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[list | None] = mapped_column("acceptanceCriteria", JSON)
    content_hash: Mapped[str] = mapped_column("contentHash", String(64), nullable=False)

    verdicts: Mapped[list[RequirementVerdict]] = relationship(back_populates="requirement_revision")


class VerificationRun(TimestampMixin, Base):
    __tablename__ = "VerificationRun"
    __table_args__ = (
        Index("VerificationRun_projectId_idx", "projectId"),
        Index("VerificationRun_snapshotId_idx", "snapshotId"),
        Index("VerificationRun_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column("snapshotId", ForeignKey("RepositorySnapshot.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(pgenum(RunStatus, "RunStatus"), default=RunStatus.PENDING, nullable=False)
    verifier_version: Mapped[str] = mapped_column("verifierVersion", String, nullable=False)
    model_name: Mapped[str | None] = mapped_column("modelName", String)
    started_at: Mapped[datetime | None] = mapped_column("startedAt", DateTime())
    completed_at: Mapped[datetime | None] = mapped_column("completedAt", DateTime())
    error_message: Mapped[str | None] = mapped_column("errorMessage", Text)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)

    snapshot: Mapped[RepositorySnapshot] = relationship(back_populates="verification_runs")
    verdicts: Mapped[list[RequirementVerdict]] = relationship(back_populates="verification_run", cascade="all, delete-orphan")


class RequirementVerdict(TimestampMixin, Base):
    __tablename__ = "RequirementVerdict"
    __table_args__ = (
        UniqueConstraint("verificationRunId", "requirementRevisionId", name="RequirementVerdict_run_revision_key"),
        CheckConstraint('confidence >= 0 AND confidence <= 1', name="RequirementVerdict_confidence_check"),
        Index("RequirementVerdict_projectId_idx", "projectId"),
        Index("RequirementVerdict_verificationRunId_idx", "verificationRunId"),
        Index("RequirementVerdict_requirementRevisionId_idx", "requirementRevisionId"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    verification_run_id: Mapped[str] = mapped_column("verificationRunId", ForeignKey("VerificationRun.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    requirement_revision_id: Mapped[str] = mapped_column("requirementRevisionId", ForeignKey("RequirementRevision.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    verdict: Mapped[VerificationVerdict] = mapped_column(pgenum(VerificationVerdict, "VerificationVerdict"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    verification_run: Mapped[VerificationRun] = relationship(back_populates="verdicts")
    requirement_revision: Mapped[RequirementRevision] = relationship(back_populates="verdicts")
    evidence_references: Mapped[list[EvidenceReference]] = relationship(back_populates="verdict", cascade="all, delete-orphan")
    overrides: Mapped[list[HumanOverride]] = relationship(back_populates="verdict_record", cascade="all, delete-orphan")


class EvidenceReference(TimestampMixin, Base):
    __tablename__ = "EvidenceReference"
    __table_args__ = (
        CheckConstraint('"startLine" > 0 AND "endLine" >= "startLine"', name="EvidenceReference_valid_lines_check"),
        Index("EvidenceReference_projectId_idx", "projectId"),
        Index("EvidenceReference_verdictId_idx", "verdictId"),
        Index("EvidenceReference_snapshotId_idx", "snapshotId"),
        Index("EvidenceReference_fileId_idx", "fileId"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    verdict_id: Mapped[str] = mapped_column("verdictId", ForeignKey("RequirementVerdict.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    snapshot_id: Mapped[str] = mapped_column("snapshotId", ForeignKey("RepositorySnapshot.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    file_id: Mapped[str] = mapped_column("fileId", ForeignKey("RepositoryFile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column("chunkId", ForeignKey("CodeChunk.id", ondelete="SET NULL", onupdate="CASCADE"))
    kind: Mapped[EvidenceKind] = mapped_column(pgenum(EvidenceKind, "EvidenceKind"), nullable=False)
    start_line: Mapped[int] = mapped_column("startLine", Integer, nullable=False)
    end_line: Mapped[int] = mapped_column("endLine", Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    quote_hash: Mapped[str] = mapped_column("quoteHash", String(64), nullable=False)
    file_content_hash: Mapped[str] = mapped_column("fileContentHash", String(64), nullable=False)
    relevance_score: Mapped[float | None] = mapped_column("relevanceScore", Float)

    verdict: Mapped[RequirementVerdict] = relationship(back_populates="evidence_references")
    chunk: Mapped[CodeChunk | None] = relationship(back_populates="evidence_references")


class HumanOverride(TimestampMixin, Base):
    __tablename__ = "HumanOverride"
    __table_args__ = (
        Index("HumanOverride_projectId_idx", "projectId"),
        Index("HumanOverride_verdictId_idx", "verdictId"),
        Index("HumanOverride_userId_idx", "userId"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    verdict_id: Mapped[str] = mapped_column("verdictId", ForeignKey("RequirementVerdict.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column("projectId", ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column("userId", ForeignKey("User.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    verdict: Mapped[VerificationVerdict] = mapped_column(pgenum(VerificationVerdict, "VerificationVerdict"), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    supersedes_override_id: Mapped[str | None] = mapped_column("supersedesOverrideId", ForeignKey("HumanOverride.id", ondelete="SET NULL", onupdate="CASCADE"))

    verdict_record: Mapped[RequirementVerdict] = relationship(back_populates="overrides", foreign_keys=[verdict_id])
