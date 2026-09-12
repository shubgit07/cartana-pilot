"""Pydantic schemas for PR verification and the PR Trust Brief."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VerificationVerdictStatusLiteral = Literal["covered", "partial", "missing", "unclear"]
VerificationConfidenceLiteral = Literal["high", "medium", "low"]
RiskAlertKindLiteral = Literal[
    "missing_backend_check",
    "no_tests",
    "scope_creep",
    "security_gap",
    "error_handling",
]
RiskAlertSeverityLiteral = Literal["critical", "warning", "info"]
PRTrustLevelLiteral = Literal["high", "medium", "low"]


class RequirementVerificationVerdict(BaseModel):
    reqId: str
    title: str
    status: VerificationVerdictStatusLiteral
    confidence: VerificationConfidenceLiteral = "high"
    evidenceFile: str | None = None
    evidenceSnippet: str | None = None
    rationale: str


class PRRiskAlert(BaseModel):
    kind: RiskAlertKindLiteral
    severity: RiskAlertSeverityLiteral
    title: str
    description: str
    affectedFiles: list[str] = Field(default_factory=list)


class ChangedFileSummary(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int


class PRTrustBrief(BaseModel):
    id: str
    projectId: str
    title: str
    coverageScore: int = Field(ge=0, le=100)
    trustLevel: PRTrustLevelLiteral
    summary: str
    totalRequirements: int
    coveredCount: int
    partialCount: int
    missingCount: int
    verdicts: list[RequirementVerificationVerdict] = Field(default_factory=list)
    riskAlerts: list[PRRiskAlert] = Field(default_factory=list)
    changedFilesSummary: list[ChangedFileSummary] = Field(default_factory=list)
    createdAt: str


class VerifyPRInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    specText: str | None = Field(default=None, max_length=50000)
    rawDiff: str | None = Field(default=None, max_length=200000)
    githubPrUrl: str | None = Field(default=None, max_length=1000)


class PRTrustBriefResponse(BaseModel):
    brief: PRTrustBrief
    fromCache: bool = False


class VerificationRunSummary(BaseModel):
    id: str
    title: str
    commitSha: str
    coverageScore: int = Field(ge=0, le=100)
    trustLevel: PRTrustLevelLiteral
    totalRequirements: int = 0
    coveredCount: int = 0
    missingCount: int = 0
    createdAt: str


class VerificationRunListResponse(BaseModel):
    runs: list[VerificationRunSummary] = Field(default_factory=list)

