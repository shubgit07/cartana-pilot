"""Source routes - upload, paste-as-text, listing, status and deletion.

Port of ``apps/api/src/modules/sources/router.ts``: routes stay thin and the
service layer owns DB and storage work. Mounted at
``/projects/{project_id}/sources``.
"""
from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.source import (
    CreateSourceFromText,
    JobStatusResponse,
    SourceListResponse,
    SourceResponse,
)
from app.api.services import source_service
from app.db.session import get_db

router = APIRouter(tags=["sources"])


@router.get("", response_model=SourceListResponse)
def list_sources(
    project_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SourceListResponse:
    return SourceListResponse(sources=source_service.list_sources(db, user.id, project_id))


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    project_id: str,
    file: UploadFile = File(..., description="Uploaded document (max 25MB)"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SourceResponse:
    data = await file.read()
    # The service is synchronous (SQLAlchemy + filesystem), so keep it off the
    # event loop.
    source = await run_in_threadpool(
        source_service.create_source_from_file,
        db,
        user.id,
        project_id,
        filename=file.filename or "upload.bin",
        data=data,
        mime_type=file.content_type,
    )
    return SourceResponse(source=source)


@router.post("/text", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source_from_text(
    project_id: str,
    payload: CreateSourceFromText,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SourceResponse:
    return SourceResponse(
        source=source_service.create_source_from_text(db, user.id, project_id, payload)
    )


@router.post("/diff", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source_from_diff(
    project_id: str,
    payload: CreateSourceFromText,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SourceResponse:
    return SourceResponse(
        source=source_service.create_source_from_text(db, user.id, project_id, payload)
    )


@router.get("/{source_id}", response_model=SourceResponse)
def get_source(
    project_id: str,
    source_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SourceResponse:
    return SourceResponse(source=source_service.get_source(db, user.id, source_id, project_id))


@router.get("/{source_id}/status", response_model=JobStatusResponse)
def get_source_status(
    project_id: str,
    source_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> JobStatusResponse:
    return JobStatusResponse(
        status=source_service.get_source_job_status(db, user.id, source_id, project_id)
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_source(
    project_id: str,
    source_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    source_service.delete_source(db, user.id, source_id, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
