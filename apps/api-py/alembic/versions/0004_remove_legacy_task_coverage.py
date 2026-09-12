"""Remove standalone tasks and legacy requirement-to-task coverage.

Revision ID: 0004_remove_legacy_task_coverage
Revises: 0003_compliance_foundations

The downgrade recreates empty legacy structures; dropped data is not
recoverable.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from alembic import op

revision = "0004_remove_legacy_task_coverage"
down_revision = "0003_compliance_foundations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("AuditFinding", "AuditRun", "CoverageLink", "TaskChunk", "Task"):
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    for enum_name in (
        "AuditFindingKind",
        "AuditSeverity",
        "CoverageOrigin",
        "CoverageStatus",
        "TaskState",
        "TaskOrigin",
    ):
        op.execute(f'DROP TYPE IF EXISTS "{enum_name}"')


def downgrade() -> None:
    task_origin = PgEnum("ai", "user", name="TaskOrigin")
    task_state = PgEnum("suggested", "accepted", "rejected", "edited", name="TaskState")
    coverage_status = PgEnum("covered", "partial", "unclear", "missing", name="CoverageStatus")
    coverage_origin = PgEnum("ai_suggested", "user_confirmed", name="CoverageOrigin")
    audit_severity = PgEnum("info", "warning", "critical", name="AuditSeverity")
    audit_kind = PgEnum(
        "uncovered_requirement", "partial_coverage", "vague_requirement",
        "deadline_risk", "orphan_task", "other", name="AuditFindingKind",
    )
    for enum_type in (task_origin, task_state, coverage_status, coverage_origin, audit_severity, audit_kind):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "Task",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("projectId", sa.String(), sa.ForeignKey("Project.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
        sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="SET NULL", onupdate="CASCADE")),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("origin", task_origin, nullable=False),
        sa.Column("state", task_state, nullable=False),
        sa.Column("dedupeKey", sa.String()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
    )
    for name, cols in (("projectId", ["projectId"]), ("userId", ["userId"]), ("requirementId", ["requirementId"]), ("state", ["state"]), ("dedupeKey", ["dedupeKey"])):
        op.create_index(f"Task_{name}_idx", "Task", cols)

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
    for name in ("projectId", "requirementId", "taskId"):
        op.create_index(f"CoverageLink_{name}_idx", "CoverageLink", [name])

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
        sa.Column("kind", audit_kind, nullable=False),
        sa.Column("severity", audit_severity, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requirementId", sa.String(), sa.ForeignKey("Requirement.id", ondelete="SET NULL", onupdate="CASCADE")),
        sa.Column("taskId", sa.String(), sa.ForeignKey("Task.id", ondelete="SET NULL", onupdate="CASCADE")),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for name in ("runId", "projectId", "severity"):
        op.create_index(f"AuditFinding_{name}_idx", "AuditFinding", [name])
