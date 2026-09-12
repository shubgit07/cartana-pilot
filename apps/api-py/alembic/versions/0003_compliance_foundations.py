"""Add immutable repository indexing and compliance verification foundations.

Revision ID: 0003_compliance_foundations
Revises: 0002_hnsw_chunk_embedding
"""
from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from alembic import op

revision = "0003_compliance_foundations"
down_revision = "0002_hnsw_chunk_embedding"
branch_labels = None
depends_on = None


def _enum(name: str, values: tuple[str, ...]) -> PgEnum:
    op.execute(
        f'DO $$ BEGIN CREATE TYPE "{name}" AS ENUM ({", ".join(repr(v) for v in values)}); '
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    return PgEnum(*values, name=name, create_type=False)


def _timestamps() -> list[sa.Column]:
    return [sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)]


def upgrade() -> None:
    provider = _enum("RepositoryProvider", ("github", "gitlab", "bitbucket", "generic_git"))
    run_status = _enum("RunStatus", ("pending", "running", "succeeded", "failed", "cancelled"))
    snapshot_kind = _enum("SnapshotKind", ("commit", "pull_request"))
    symbol_kind = _enum("SymbolKind", ("module", "class", "function", "method", "interface", "type", "constant", "other"))
    verdict = _enum("VerificationVerdict", ("satisfied", "partial", "not_satisfied", "inconclusive", "not_applicable"))
    evidence_kind = _enum("EvidenceKind", ("supporting", "contradicting", "context"))

    op.create_table("RepositoryConnection", sa.Column("id", sa.String(), primary_key=True), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("provider", provider, nullable=False), sa.Column("externalId", sa.String(), nullable=False), sa.Column("cloneUrl", sa.Text(), nullable=False), sa.Column("defaultBranch", sa.String(), nullable=False), sa.Column("displayName", sa.String(), nullable=False), sa.Column("isActive", sa.Boolean(), server_default=sa.text("true"), nullable=False), sa.Column("updatedAt", sa.DateTime(), nullable=False), *_timestamps(), sa.UniqueConstraint("projectId", "provider", "externalId", name="RepositoryConnection_project_provider_external_key"))
    op.create_index("RepositoryConnection_projectId_idx", "RepositoryConnection", ["projectId"]); op.create_index("RepositoryConnection_userId_idx", "RepositoryConnection", ["userId"])

    op.create_table("RepositorySnapshot", sa.Column("id", sa.String(), primary_key=True), sa.Column("repositoryId", sa.String(), sa.ForeignKey("RepositoryConnection.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("kind", snapshot_kind, nullable=False), sa.Column("commitSha", sa.String(64), nullable=False), sa.Column("treeSha", sa.String(64)), sa.Column("refName", sa.String()), sa.Column("baseCommitSha", sa.String(64)), sa.Column("pullRequestNumber", sa.Integer()), sa.Column("committedAt", sa.DateTime()), sa.Column("metadata", sa.JSON()), *_timestamps(), sa.UniqueConstraint("repositoryId", "commitSha", name="RepositorySnapshot_repository_commit_key"))
    for n, c in (("projectId", "projectId"), ("repositoryId", "repositoryId"), ("commitSha", "commitSha")): op.create_index(f"RepositorySnapshot_{n}_idx", "RepositorySnapshot", [c])

    op.create_table("RepositoryFile", sa.Column("id", sa.String(), primary_key=True), sa.Column("snapshotId", sa.String(), sa.ForeignKey("RepositorySnapshot.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("path", sa.Text(), nullable=False), sa.Column("blobSha", sa.String(64), nullable=False), sa.Column("contentHash", sa.String(64), nullable=False), sa.Column("language", sa.String()), sa.Column("sizeBytes", sa.Integer(), nullable=False), sa.Column("lineCount", sa.Integer()), sa.Column("isBinary", sa.Boolean(), server_default=sa.text("false"), nullable=False), *_timestamps(), sa.UniqueConstraint("snapshotId", "path", name="RepositoryFile_snapshot_path_key"))
    for n in ("projectId", "snapshotId", "blobSha"): op.create_index(f"RepositoryFile_{n}_idx", "RepositoryFile", [n])

    op.create_table("CodeSymbol", sa.Column("id", sa.String(), primary_key=True), sa.Column("fileId", sa.String(), sa.ForeignKey("RepositoryFile.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("kind", symbol_kind, nullable=False), sa.Column("name", sa.String(), nullable=False), sa.Column("qualifiedName", sa.Text(), nullable=False), sa.Column("signature", sa.Text()), sa.Column("startLine", sa.Integer(), nullable=False), sa.Column("endLine", sa.Integer(), nullable=False), sa.Column("symbolHash", sa.String(64), nullable=False), *_timestamps(), sa.CheckConstraint('"startLine" > 0 AND "endLine" >= "startLine"', name="CodeSymbol_valid_lines_check"), sa.UniqueConstraint("fileId", "qualifiedName", "startLine", name="CodeSymbol_file_name_line_key"))
    for n in ("projectId", "fileId", "qualifiedName"): op.create_index(f"CodeSymbol_{n}_idx", "CodeSymbol", [n])

    op.create_table("IndexRun", sa.Column("id", sa.String(), primary_key=True), sa.Column("snapshotId", sa.String(), sa.ForeignKey("RepositorySnapshot.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("status", run_status, server_default="pending", nullable=False), sa.Column("indexVersion", sa.String(), nullable=False), sa.Column("embeddingModel", sa.String()), sa.Column("embeddingDimension", sa.Integer(), server_default="768", nullable=False), sa.Column("startedAt", sa.DateTime()), sa.Column("completedAt", sa.DateTime()), sa.Column("errorMessage", sa.Text()), sa.Column("stats", sa.JSON()), *_timestamps(), sa.CheckConstraint('"embeddingDimension" = 768', name="IndexRun_embedding_dimension_check"))
    for n in ("projectId", "snapshotId", "status"): op.create_index(f"IndexRun_{n}_idx", "IndexRun", [n])

    op.create_table("CodeChunk", sa.Column("id", sa.String(), primary_key=True), sa.Column("indexRunId", sa.String(), sa.ForeignKey("IndexRun.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("fileId", sa.String(), sa.ForeignKey("RepositoryFile.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("ordinal", sa.Integer(), nullable=False), sa.Column("startLine", sa.Integer(), nullable=False), sa.Column("endLine", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("contentHash", sa.String(64), nullable=False), sa.Column("tokenCount", sa.Integer()), sa.Column("embedding", Vector(768)), *_timestamps(), sa.CheckConstraint('"startLine" > 0 AND "endLine" >= "startLine"', name="CodeChunk_valid_lines_check"), sa.UniqueConstraint("indexRunId", "fileId", "ordinal", name="CodeChunk_run_file_ordinal_key"))
    for n in ("projectId", "fileId", "indexRunId", "contentHash"): op.create_index(f"CodeChunk_{n}_idx", "CodeChunk", [n])

    op.create_table("RequirementRevision", sa.Column("id", sa.String(), primary_key=True), sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("title", sa.String(), nullable=False), sa.Column("description", sa.Text()), sa.Column("acceptanceCriteria", sa.JSON()), sa.Column("contentHash", sa.String(64), nullable=False), *_timestamps(), sa.UniqueConstraint("requirementId", "revision", name="RequirementRevision_requirement_revision_key"), sa.UniqueConstraint("requirementId", "contentHash", name="RequirementRevision_requirement_hash_key"))
    for n in ("projectId", "requirementId"): op.create_index(f"RequirementRevision_{n}_idx", "RequirementRevision", [n])

    op.create_table("VerificationRun", sa.Column("id", sa.String(), primary_key=True), sa.Column("snapshotId", sa.String(), sa.ForeignKey("RepositorySnapshot.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("status", run_status, server_default="pending", nullable=False), sa.Column("verifierVersion", sa.String(), nullable=False), sa.Column("modelName", sa.String()), sa.Column("startedAt", sa.DateTime()), sa.Column("completedAt", sa.DateTime()), sa.Column("errorMessage", sa.Text()), sa.Column("metadata", sa.JSON()), *_timestamps())
    for n in ("projectId", "snapshotId", "status"): op.create_index(f"VerificationRun_{n}_idx", "VerificationRun", [n])

    op.create_table("RequirementVerdict", sa.Column("id", sa.String(), primary_key=True), sa.Column("verificationRunId", sa.String(), sa.ForeignKey("VerificationRun.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("requirementRevisionId", sa.String(), sa.ForeignKey("RequirementRevision.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("verdict", verdict, nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("rationale", sa.Text(), nullable=False), *_timestamps(), sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="RequirementVerdict_confidence_check"), sa.UniqueConstraint("verificationRunId", "requirementRevisionId", name="RequirementVerdict_run_revision_key"))
    for n in ("projectId", "verificationRunId", "requirementRevisionId"): op.create_index(f"RequirementVerdict_{n}_idx", "RequirementVerdict", [n])

    op.create_table("EvidenceReference", sa.Column("id", sa.String(), primary_key=True), sa.Column("verdictId", sa.String(), sa.ForeignKey("RequirementVerdict.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("snapshotId", sa.String(), sa.ForeignKey("RepositorySnapshot.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False), sa.Column("fileId", sa.String(), sa.ForeignKey("RepositoryFile.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False), sa.Column("chunkId", sa.String(), sa.ForeignKey("CodeChunk.id", ondelete="SET NULL", onupdate="CASCADE")), sa.Column("kind", evidence_kind, nullable=False), sa.Column("startLine", sa.Integer(), nullable=False), sa.Column("endLine", sa.Integer(), nullable=False), sa.Column("quote", sa.Text(), nullable=False), sa.Column("quoteHash", sa.String(64), nullable=False), sa.Column("fileContentHash", sa.String(64), nullable=False), sa.Column("relevanceScore", sa.Float()), *_timestamps(), sa.CheckConstraint('"startLine" > 0 AND "endLine" >= "startLine"', name="EvidenceReference_valid_lines_check"))
    for n in ("projectId", "verdictId", "snapshotId", "fileId"): op.create_index(f"EvidenceReference_{n}_idx", "EvidenceReference", [n])

    op.create_table("HumanOverride", sa.Column("id", sa.String(), primary_key=True), sa.Column("verdictId", sa.String(), sa.ForeignKey("RequirementVerdict.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False), sa.Column("verdict", verdict, nullable=False), sa.Column("rationale", sa.Text(), nullable=False), sa.Column("supersedesOverrideId", sa.String(), sa.ForeignKey("HumanOverride.id", ondelete="SET NULL", onupdate="CASCADE")), *_timestamps())
    for n in ("projectId", "verdictId", "userId"): op.create_index(f"HumanOverride_{n}_idx", "HumanOverride", [n])


def downgrade() -> None:
    for table in ("HumanOverride", "EvidenceReference", "RequirementVerdict", "VerificationRun", "RequirementRevision", "CodeChunk", "IndexRun", "CodeSymbol", "RepositoryFile", "RepositorySnapshot", "RepositoryConnection"):
        op.drop_table(table)
    for name in ("EvidenceKind", "VerificationVerdict", "SymbolKind", "SnapshotKind", "RunStatus", "RepositoryProvider"):
        op.execute(f'DROP TYPE IF EXISTS "{name}"')
