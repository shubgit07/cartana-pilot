"""Pydantic schemas for the repository index (sync + status)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RepoFileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=1024)
    content: str = Field(max_length=500_000)


class SyncRepositoryInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    files: list[RepoFileInput] = Field(default_factory=list, max_length=500)
    commitSha: str | None = Field(default=None, max_length=64)
    refName: str | None = Field(default=None, max_length=512)


class SyncRepositoryResponse(BaseModel):
    snapshotId: str
    commitSha: str
    filesIndexed: int
    chunksCreated: int
    skipped: list[str] = Field(default_factory=list)
    embeddingModel: str
    embeddingDim: int


class RepositoryStatusResponse(BaseModel):
    connected: bool = False
    commitSha: str | None = None
    refName: str | None = None
    indexedFilesCount: int = 0
    codeChunksCount: int = 0
    embeddingDim: int = 768
    status: str = "pending"
    files: list[RepoFileStatus] = Field(default_factory=list)


class RepoFileStatus(BaseModel):
    path: str
    language: str | None = None
    lineCount: int | None = None
    sizeBytes: int = 0
    chunksCount: int = 0
