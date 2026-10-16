"""Add deterministic evidence-verification flag to requirement verdicts.

Revision ID: 0005_evidence_verified
Revises: 0004_remove_legacy_task_coverage

A null flag means the verdict claimed no evidence (missing/unclear);
true/false records whether a claimed snippet was found in the diff.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_evidence_verified"
down_revision = "0004_remove_legacy_task_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "RequirementVerdict",
        sa.Column("evidenceVerified", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("RequirementVerdict", "evidenceVerified")
