"""Repository index routes — sync a workspace snapshot and report index status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.repository import (
    RepoFileStatus,
    RepositoryStatusResponse,
    SyncRepositoryInput,
    SyncRepositoryResponse,
)
from app.api.services import repo_index_service
from app.api.services.repo_index_service import IndexFileInput
from app.config import get_settings
from app.db.models import (
    CodeChunk,
    IndexRun,
    RepositoryConnection,
    RepositoryFile,
    RepositorySnapshot,
)
from app.db.session import get_db

router = APIRouter(tags=["repository"])


@router.post("/sync", response_model=SyncRepositoryResponse)
def sync_repository(
    project_id: str,
    payload: SyncRepositoryInput,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SyncRepositoryResponse:
    """Chunk + embed the supplied files into the project's code index."""
    result = repo_index_service.sync_repository_snapshot(
        db,
        project_id=project_id,
        user_id=user.id,
        files=[IndexFileInput(path=f.path, content=f.content) for f in payload.files],
        commit_sha=payload.commitSha,
        ref_name=payload.refName,
    )
    return SyncRepositoryResponse(
        snapshotId=result.snapshot_id,
        commitSha=result.commit_sha,
        filesIndexed=result.files_indexed,
        chunksCreated=result.chunks_created,
        skipped=result.skipped,
        embeddingModel=result.embedding_model,
        embeddingDim=result.embedding_dim,
    )


@router.get("/status", response_model=RepositoryStatusResponse)
def repository_status(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> RepositoryStatusResponse:
    """Latest snapshot + index stats for the Repository panel."""
    connection = db.execute(
        select(RepositoryConnection).where(RepositoryConnection.project_id == project_id)
    ).scalar_one_or_none()
    if connection is None:
        return RepositoryStatusResponse()
    snapshot = db.execute(
        select(RepositorySnapshot)
        .where(RepositorySnapshot.repository_id == connection.id)
        .order_by(RepositorySnapshot.created_at.desc())
    ).scalars().first()
    if snapshot is None:
        return RepositoryStatusResponse(connected=True)
    files_count = db.execute(
        select(func.count())
        .select_from(RepositoryFile)
        .where(RepositoryFile.snapshot_id == snapshot.id)
    ).scalar_one()
    chunks_count = db.execute(
        select(func.count())
        .select_from(CodeChunk)
        .join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id)
        .where(RepositoryFile.snapshot_id == snapshot.id)
    ).scalar_one()
    latest_run = db.execute(
        select(IndexRun)
        .where(IndexRun.snapshot_id == snapshot.id)
        .order_by(IndexRun.created_at.desc())
    ).scalars().first()
    status = "pending"
    if latest_run is not None:
        status = {"succeeded": "synced", "running": "indexing", "pending": "pending"}.get(
            latest_run.status.value if hasattr(latest_run.status, "value") else str(latest_run.status),
            "pending",
        )
    chunk_count_rows = db.execute(
        select(CodeChunk.file_id, func.count())
        .join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id)
        .where(RepositoryFile.snapshot_id == snapshot.id)
        .group_by(CodeChunk.file_id)
    ).all()
    chunk_counts: dict[str, int] = {row[0]: row[1] for row in chunk_count_rows}
    file_rows = db.execute(
        select(RepositoryFile)
        .where(RepositoryFile.snapshot_id == snapshot.id)
        .order_by(RepositoryFile.path.asc())
        .limit(100)
    ).scalars().all()
    return RepositoryStatusResponse(
        connected=True,
        commitSha=snapshot.commit_sha,
        refName=snapshot.ref_name,
        indexedFilesCount=files_count,
        codeChunksCount=chunks_count,
        embeddingDim=get_settings().embedding_dim,
        status=status,
        files=[
            RepoFileStatus(
                path=f.path,
                language=f.language,
                lineCount=f.line_count,
                sizeBytes=f.size_bytes,
                chunksCount=chunk_counts.get(f.id, 0),
            )
            for f in file_rows
        ],
    )
