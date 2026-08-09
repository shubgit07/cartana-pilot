"""Initial schema: mirrors apps/api/prisma/migrations (init + dedupeKey).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-28
"""
from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    enums = [
        ('SourceKind', "('pdf', 'text')"),
        ('SourceStatus', "('uploaded', 'processing', 'processed', 'failed')"),
        ('RequirementOrigin', "('ai', 'user')"),
        ('RequirementState', "('suggested', 'accepted', 'rejected', 'edited')"),
        ('TaskOrigin', "('ai', 'user')"),
        ('TaskState', "('suggested', 'accepted', 'rejected', 'edited')"),
        ('CoverageStatus', "('covered', 'partial', 'unclear', 'missing')"),
        ('CoverageOrigin', "('ai_suggested', 'user_confirmed')"),
        ('AuditSeverity', "('info', 'warning', 'critical')"),
        ('AuditFindingKind', "('uncovered_requirement', 'partial_coverage', 'vague_requirement', 'deadline_risk', 'orphan_task', 'other')"),
    ]
    for name, vals in enums:
        op.execute(f"""
        DO $$ BEGIN
            CREATE TYPE "{name}" AS ENUM {vals};
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """)

    source_kind = PgEnum("pdf", "text", name="SourceKind", create_type=False)
    source_status = PgEnum("uploaded", "processing", "processed", "failed", name="SourceStatus", create_type=False)
    requirement_origin = PgEnum("ai", "user", name="RequirementOrigin", create_type=False)
    requirement_state = PgEnum("suggested", "accepted", "rejected", "edited", name="RequirementState", create_type=False)
    task_origin = PgEnum("ai", "user", name="TaskOrigin", create_type=False)
    task_state = PgEnum("suggested", "accepted", "rejected", "edited", name="TaskState", create_type=False)
    coverage_status = PgEnum("covered", "partial", "unclear", "missing", name="CoverageStatus", create_type=False)
    coverage_origin = PgEnum("ai_suggested", "user_confirmed", name="CoverageOrigin", create_type=False)
    audit_severity = PgEnum("info", "warning", "critical", name="AuditSeverity", create_type=False)
    audit_finding_kind = PgEnum(
        "uncovered_requirement", "partial_coverage", "vague_requirement",
        "deadline_risk", "orphan_task", "other", name="AuditFindingKind", create_type=False,
    )

    op.create_table(
        "User",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), unique=True),
        sa.Column("name", sa.String()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "Project",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )
    op.create_index("Project_userId_idx", "Project", ["userId"])
    op.create_index("Project_createdAt_idx", "Project", ["createdAt"])

    op.create_table(
        "Source",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("kind", source_kind, nullable=False),
        sa.Column("status", source_status, nullable=False, server_default="uploaded"),
        sa.Column("storageKey", sa.String(), nullable=False),
        sa.Column("mimeType", sa.String()),
        sa.Column("sizeBytes", sa.Integer()),
        sa.Column("errorMessage", sa.Text()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )
    op.create_index("Source_projectId_idx", "Source", ["projectId"])
    op.create_index("Source_userId_idx", "Source", ["userId"])
    op.create_index("Source_status_idx", "Source", ["status"])

    op.create_table(
        "Chunk",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("sourceId", sa.String(), sa.ForeignKey("Source.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("Chunk_sourceId_idx", "Chunk", ["sourceId"])
    op.create_index("Chunk_position_idx", "Chunk", ["position"])

    op.create_table(
        "Requirement",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("origin", requirement_origin, nullable=False, server_default="ai"),
        sa.Column("state", requirement_state, nullable=False, server_default="suggested"),
        sa.Column("dedupeKey", sa.String()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )
    op.create_index("Requirement_projectId_idx", "Requirement", ["projectId"])
    op.create_index("Requirement_userId_idx", "Requirement", ["userId"])
    op.create_index("Requirement_state_idx", "Requirement", ["state"])
    op.create_index("Requirement_dedupeKey_idx", "Requirement", ["dedupeKey"])

    op.create_table(
        "RequirementChunk",
        sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True),
        sa.Column("chunkId", sa.String(), sa.ForeignKey("Chunk.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True),
    )
    op.create_index("RequirementChunk_chunkId_idx", "RequirementChunk", ["chunkId"])

    op.create_table(
        "Task",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="SET NULL", onupdate="CASCADE")),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("origin", task_origin, nullable=False, server_default="ai"),
        sa.Column("state", task_state, nullable=False, server_default="suggested"),
        sa.Column("dedupeKey", sa.String()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )
    op.create_index("Task_projectId_idx", "Task", ["projectId"])
    op.create_index("Task_userId_idx", "Task", ["userId"])
    op.create_index("Task_requirementId_idx", "Task", ["requirementId"])
    op.create_index("Task_state_idx", "Task", ["state"])
    op.create_index("Task_dedupeKey_idx", "Task", ["dedupeKey"])

    op.create_table(
        "TaskChunk",
        sa.Column("taskId", sa.String(), sa.ForeignKey("Task.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True),
        sa.Column("chunkId", sa.String(), sa.ForeignKey("Chunk.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True),
    )
    op.create_index("TaskChunk_chunkId_idx", "TaskChunk", ["chunkId"])

    op.create_table(
        "CoverageLink",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("taskId", sa.String(), sa.ForeignKey("Task.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("status", coverage_status, nullable=False),
        sa.Column("origin", coverage_origin, nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("requirementId", "taskId", name="CoverageLink_requirementId_taskId_key"),
    )
    op.create_index("CoverageLink_projectId_idx", "CoverageLink", ["projectId"])
    op.create_index("CoverageLink_requirementId_idx", "CoverageLink", ["requirementId"])
    op.create_index("CoverageLink_taskId_idx", "CoverageLink", ["taskId"])

    op.create_table(
        "AuditRun",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("AuditRun_projectId_idx", "AuditRun", ["projectId"])
    op.create_index("AuditRun_createdAt_idx", "AuditRun", ["createdAt"])

    op.create_table(
        "AuditFinding",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("runId", sa.String(), sa.ForeignKey("AuditRun.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("projectId", sa.String(), nullable=False),
        sa.Column("kind", audit_finding_kind, nullable=False),
        sa.Column("severity", audit_severity, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="SET NULL", onupdate="CASCADE")),
        sa.Column("taskId", sa.String(), sa.ForeignKey("Task.id", ondelete="SET NULL", onupdate="CASCADE")),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("AuditFinding_runId_idx", "AuditFinding", ["runId"])
    op.create_index("AuditFinding_projectId_idx", "AuditFinding", ["projectId"])
    op.create_index("AuditFinding_severity_idx", "AuditFinding", ["severity"])


def downgrade() -> None:
    op.drop_table("AuditFinding")
    op.drop_table("AuditRun")
    op.drop_table("CoverageLink")
    op.drop_table("TaskChunk")
    op.drop_table("Task")
    op.drop_table("RequirementChunk")
    op.drop_table("Requirement")
    op.drop_table("Chunk")
    op.drop_table("Source")
    op.drop_table("Project")
    op.drop_table("User")

    bind = op.get_bind()
    for enum_name in (
        "AuditFindingKind", "AuditSeverity", "CoverageOrigin", "CoverageStatus",
        "TaskState", "TaskOrigin", "RequirementState", "RequirementOrigin",
        "SourceStatus", "SourceKind",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
