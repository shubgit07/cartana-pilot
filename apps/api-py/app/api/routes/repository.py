"""Repository index routes — connect a GitHub repo, sync, and report status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.repository import (
    CommitListResponse,
    ConnectRepositoryInput,
    ConnectRepositoryResponse,
    GitHubCommitItem,
    GitHubPullItem,
    PullListResponse,
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
    RepositoryProvider,
    RepositorySnapshot,
)
from app.db.session import get_db

router = APIRouter(tags=["repository"])


def _to_connect_response(result: repo_index_service.GitHubSyncResult) -> ConnectRepositoryResponse:
    return ConnectRepositoryResponse(
        connectionId=result.connection_id,
        repoUrl=result.repo_url,
        displayName=result.display_name,
        defaultBranch=result.default_branch,
        commitSha=result.commit_sha,
        filesIndexed=result.files_indexed,
        chunksCreated=result.chunks_created,
        skipped=result.skipped,
        upToDate=result.up_to_date,
    )


@router.post("/connect", response_model=ConnectRepositoryResponse)
def connect_repository(
    project_id: str,
    payload: ConnectRepositoryInput,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ConnectRepositoryResponse:
    """Link a public GitHub repo (URL-only) and build the Codebase Index."""
    return _to_connect_response(
        repo_index_service.connect_repository(db, project_id=project_id, user_id=user.id, repo_url=payload.repoUrl)
    )


@router.post("/resync", response_model=ConnectRepositoryResponse)
def resync_repository(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ConnectRepositoryResponse:
    """Refresh the Codebase Index to the repo's current HEAD (no-op when current)."""
    return _to_connect_response(
        repo_index_service.resync_repository(db, project_id=project_id, user_id=user.id)
    )


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def disconnect_repository(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Unlink the repo: connections + snapshots + code vectors are purged. Docs stay."""
    repo_index_service.disconnect_repository(db, project_id=project_id, user_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/pulls", response_model=PullListResponse)
def list_pulls(
    project_id: str,
    state: str = Query(default="open", max_length=10),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PullListResponse:
    pulls = repo_index_service.list_repo_pulls(
        db, project_id=project_id, user_id=user.id, state=state, limit=limit
    )
    return PullListResponse(pulls=[
        GitHubPullItem(
            number=p.number, title=p.title, headSha=p.head_sha,
            baseBranch=p.base_branch, updatedAt=p.updated_at, url=p.url, author=p.author,
        )
        for p in pulls
    ])


@router.get("/commits", response_model=CommitListResponse)
def list_commits(
    project_id: str,
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CommitListResponse:
    commits = repo_index_service.list_repo_commits(
        db, project_id=project_id, user_id=user.id, limit=limit
    )
    return CommitListResponse(commits=[
        GitHubCommitItem(sha=c.sha, message=c.message, author=c.author, date=c.date, url=c.url)
        for c in commits
    ])


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
    """Latest snapshot + Codebase Index stats for the Repository panel."""
    connections = db.execute(
        select(RepositoryConnection)
        .where(RepositoryConnection.project_id == project_id)
        .order_by(RepositoryConnection.created_at.desc())
    ).scalars().all()
    if not connections:
        return RepositoryStatusResponse()
    # Prefer the linked GitHub repo over legacy manual-upload snapshots.
    connection = next(
        (c for c in connections if c.provider == RepositoryProvider.GITHUB),
        connections[0],
    )
    repo_url = (
        f"https://github.com/{connection.external_id}"
        if connection.provider == RepositoryProvider.GITHUB
        else None
    )
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
        repoUrl=repo_url,
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
