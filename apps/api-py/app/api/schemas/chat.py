"""Pydantic schemas for the Chat module.

Mirrors ``ChatMessage``, ``ChatCitation``, ``ChatResponse`` in
``packages/shared/src/types.ts`` and ``ChatAskSchema`` in
``packages/shared/src/schemas.ts``.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatCitation(BaseModel):
    sourceId: str
    filename: str
    chunkId: str
    snippet: str
    score: float


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    citations: Optional[list[ChatCitation]] = None
    createdAt: str


class ChatResponse(BaseModel):
    message: ChatMessage


class ChatAsk(BaseModel):
    """Mirrors ``ChatAskSchema``."""

    model_config = ConfigDict(extra="ignore")

    question: str = Field(min_length=1, max_length=4000)
    history: Optional[list[ChatMessage]] = Field(default=None, max_length=40)


class ChatHistoryItem(BaseModel):
    """Simplified history item for the AI provider input."""
    role: Literal["user", "assistant"]
    content: str
