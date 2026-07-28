"""Chat routes — single endpoint per project.

Port of ``apps/api/src/modules/chat/router.ts``. Mounted at
``/projects/{project_id}/chat``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas.chat import ChatAsk, ChatResponse
from app.api.services import chat_service
from app.db.session import get_db

router = APIRouter(tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_project(
    project_id: str,
    payload: ChatAsk,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    return chat_service.ask_project(db, user.id, project_id, payload)
