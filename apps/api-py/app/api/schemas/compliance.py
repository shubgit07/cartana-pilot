"""Stable contracts for the requirement-to-implementation compliance domain."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RunStatusLiteral = Literal["pending", "running", "succeeded", "failed", "cancelled"]
VerdictLiteral = Literal[
    "satisfied", "partial", "not_satisfied", "inconclusive", "not_applicable"
]
EvidenceKindLiteral = Literal["supporting", "contradicting", "context"]


class RepositoryConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["github", "gitlab", "bitbucket", "generic_git"]
    externalId: str = Field(min_length=1, max_length=512)
    cloneUrl: str = Field(min_length=1, max_length=4096)
    defaultBranch: str = Field(min_length=1, max_length=512)
    displayName: str = Field(min_length=1, max_length=512)


class SnapshotIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repositoryId: str
    snapshotId: str
    commitSha: str = Field(min_length=7, max_length=64)
    treeSha: str | None = Field(default=None, max_length=64)


class RequirementRevisionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    requirementId: str
    projectId: str
    revision: int = Field(ge=1)
    title: str
    description: str | None = None
    acceptanceCriteria: list[str] = Field(default_factory=list)
    contentHash: str = Field(min_length=64, max_length=64)


class EvidenceReferenceContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshotId: str
    fileId: str
    chunkId: str | None = None
    kind: EvidenceKindLiteral
    path: str
    startLine: int = Field(ge=1)
    endLine: int = Field(ge=1)
    quote: str = Field(min_length=1)
    quoteHash: str = Field(min_length=64, max_length=64)
    fileContentHash: str = Field(min_length=64, max_length=64)
    relevanceScore: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_line_range(self) -> EvidenceReferenceContract:
        if self.endLine < self.startLine:
            raise ValueError("endLine must be greater than or equal to startLine")
        return self


class RequirementVerdictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirementRevisionId: str
    verdict: VerdictLiteral
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    evidence: list[EvidenceReferenceContract] = Field(default_factory=list)


class VerificationRunContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    projectId: str
    snapshot: SnapshotIdentity
    status: RunStatusLiteral
    verifierVersion: str
    modelName: str | None = None
    verdicts: list[RequirementVerdictContract] = Field(default_factory=list)


class HumanOverrideCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: VerdictLiteral
    rationale: str = Field(min_length=1, max_length=8000)
    supersedesOverrideId: str | None = None
