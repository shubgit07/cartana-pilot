"""Pydantic schemas for the Audit + Coverage modules.

Mirrors ``CoverageLinkSummary``, ``AuditFindingSummary``, ``AuditRunSummary``,
``AuditRunDetail`` in ``packages/shared/src/types.ts`` and
``UpdateCoverageLinkSchema`` in ``packages/shared/src/schemas.ts``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.serialization import enum_value, to_iso8601

if TYPE_CHECKING:
    from app.db.models import AuditFinding, AuditRun, CoverageLink

CoverageStatusLiteral = Literal["covered", "partial", "unclear", "missing"]
CoverageOriginLiteral = Literal["ai_suggested", "user_confirmed"]
AuditSeverityLiteral = Literal["info", "warning", "critical"]
AuditFindingKindLiteral = Literal[
    "uncovered_requirement", "partial_coverage", "vague_requirement",
    "deadline_risk", "orphan_task", "other",
]


class CoverageLinkSummary(BaseModel):
    id: str
    projectId: str
    requirementId: str
    requirementTitle: str
    taskId: str
    taskTitle: str
    status: CoverageStatusLiteral
    origin: CoverageOriginLiteral
    rationale: Optional[str] = None
    createdAt: str
    updatedAt: str

    @classmethod
    def from_model(cls, link: "CoverageLink") -> "CoverageLinkSummary":
        return cls(
            id=link.id,
            projectId=link.project_id,
            requirementId=link.requirement_id,
            requirementTitle=link.requirement.title if link.requirement else "",
            taskId=link.task_id,
            taskTitle=link.task.title if link.task else "",
            status=enum_value(link.status),
            origin=enum_value(link.origin),
            rationale=link.rationale,
            createdAt=to_iso8601(link.created_at),
            updatedAt=to_iso8601(link.updated_at),
        )


class AuditFindingSummary(BaseModel):
    id: str
    runId: str
    kind: AuditFindingKindLiteral
    severity: AuditSeverityLiteral
    message: str
    requirementId: Optional[str] = None
    requirementTitle: Optional[str] = None
    taskId: Optional[str] = None
    taskTitle: Optional[str] = None
    createdAt: str

    @classmethod
    def from_model(cls, finding: "AuditFinding") -> "AuditFindingSummary":
        return cls(
            id=finding.id,
            runId=finding.run_id,
            kind=enum_value(finding.kind),
            severity=enum_value(finding.severity),
            message=finding.message,
            requirementId=finding.requirement_id,
            requirementTitle=finding.requirement.title if finding.requirement else None,
            taskId=finding.task_id,
            taskTitle=finding.task.title if finding.task else None,
            createdAt=to_iso8601(finding.created_at),
        )


class AuditRunSummary(BaseModel):
    id: str
    projectId: str
    summary: Optional[str] = None
    findingCount: int
    criticalCount: int
    warningCount: int
    infoCount: int
    createdAt: str

    @classmethod
    def from_model(
        cls,
        run: "AuditRun",
        findings: list["AuditFinding"],
    ) -> "AuditRunSummary":
        return cls(
            id=run.id,
            projectId=run.project_id,
            summary=run.summary,
            findingCount=len(findings),
            criticalCount=sum(1 for f in findings if f.severity.value == "critical"),
            warningCount=sum(1 for f in findings if f.severity.value == "warning"),
            infoCount=sum(1 for f in findings if f.severity.value == "info"),
            createdAt=to_iso8601(run.created_at),
        )


class AuditRunDetail(AuditRunSummary):
    findings: list[AuditFindingSummary]
    coverageLinks: list[CoverageLinkSummary]


# ---- Response envelopes ----


class AuditRunListResponse(BaseModel):
    runs: list[AuditRunSummary]


class AuditRunDetailResponse(BaseModel):
    run: Optional[AuditRunDetail] = None


class AuditRunResponse(BaseModel):
    jobId: str
    status: str


class AuditJobStatusResponse(BaseModel):
    jobId: str
    state: str
    result: Optional[object] = None


class CoverageLinkListResponse(BaseModel):
    coverageLinks: list[CoverageLinkSummary]


class CoverageLinkResponse(BaseModel):
    coverageLink: CoverageLinkSummary


# ---- Input schemas ----


class UpdateCoverageLink(BaseModel):
    """Mirrors ``UpdateCoverageLinkSchema``."""

    model_config = ConfigDict(extra="ignore")

    status: Optional[CoverageStatusLiteral] = None
    rationale: Optional[str] = Field(default=None, max_length=2000)
