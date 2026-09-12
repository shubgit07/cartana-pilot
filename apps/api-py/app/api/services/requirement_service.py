"""Requirements module — service layer.

Port of ``apps/api/src/modules/requirements/service.ts``. All queries filtered
by ``user_id`` + ``project_id``. Includes idempotent upsert + stale-out helpers
used by the extraction job (though those live in the ARQ task module now).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.requirement import (
    ChunkLink,
    RequirementDetail,
    RequirementSummary,
    SourceLink,
    UpdateRequirement,
)
from app.api.services.project_service import get_owned_project
from app.core.errors import NotFoundError
from app.db.models import (
    Chunk,
    Requirement,
    RequirementChunk,
    RequirementOrigin,
    RequirementState,
    Source,
)


def _load_chunk_links(
    db: Session, requirement_ids: list[str]
) -> dict[str, list[ChunkLink]]:
    if not requirement_ids:
        return {}
    links = (
        db.execute(
            select(RequirementChunk, Chunk, Source)
            .join(Chunk, Chunk.id == RequirementChunk.chunk_id)
            .join(Source, Source.id == Chunk.source_id)
            .where(RequirementChunk.requirement_id.in_(requirement_ids))
        )
        .all()
    )
    result: dict[str, list[ChunkLink]] = {}
    for rc, chunk, source in links:
        snippet = chunk.text[:240] + "\u2026" if len(chunk.text) > 240 else chunk.text
        result.setdefault(rc.requirement_id, []).append(
            ChunkLink(chunkId=chunk.id, sourceId=source.id, filename=source.filename, snippet=snippet)
        )
    return result


def _load_source_links(
    db: Session, requirement_ids: list[str]
) -> dict[str, list[SourceLink]]:
    if not requirement_ids:
        return {}
    links = (
        db.execute(
            select(RequirementChunk, Source)
            .join(Chunk, Chunk.id == RequirementChunk.chunk_id)
            .join(Source, Source.id == Chunk.source_id)
            .where(RequirementChunk.requirement_id.in_(requirement_ids))
        )
        .all()
    )
    result: dict[str, list[SourceLink]] = {}
    seen_sources: dict[str, set[str]] = {}
    for rc, source in links:
        seen = seen_sources.setdefault(rc.requirement_id, set())
        if source.id not in seen:
            seen.add(source.id)
            result.setdefault(rc.requirement_id, []).append(
                SourceLink(sourceId=source.id, filename=source.filename)
            )
    return result


def list_requirements(db: Session, user_id: str, project_id: str) -> list[RequirementSummary]:
    get_owned_project(db, user_id, project_id)

    rows = db.execute(
        select(Requirement)
        .where(Requirement.project_id == project_id, Requirement.user_id == user_id)
        .order_by(Requirement.state.asc(), Requirement.created_at.desc())
    ).scalars().all()
    if not rows:
        return []

    source_links = _load_source_links(db, [r.id for r in rows])
    return [RequirementSummary.from_model(r, source_links.get(r.id, [])) for r in rows]


def get_requirement(
    db: Session, user_id: str, project_id: str, req_id: str
) -> RequirementDetail:
    row = db.execute(
        select(Requirement).where(
            Requirement.id == req_id,
            Requirement.project_id == project_id,
            Requirement.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Requirement not found")

    chunk_links = _load_chunk_links(db, [row.id])
    source_links = _load_source_links(db, [row.id])
    summary = RequirementSummary.from_model(row, source_links.get(row.id, []))
    return RequirementDetail(**summary.model_dump(), chunkLinks=chunk_links.get(row.id, []))


def update_requirement(
    db: Session,
    user_id: str,
    project_id: str,
    req_id: str,
    payload: UpdateRequirement,
) -> RequirementSummary:
    row = db.execute(
        select(Requirement).where(
            Requirement.id == req_id,
            Requirement.project_id == project_id,
            Requirement.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Requirement not found")

    changes = payload.model_dump(exclude_unset=True)
    touched = bool(changes)

    next_state = changes.get("state", row.state.value)
    if touched and next_state == "suggested" and row.origin.value == "ai":
        final_state = "edited"
    else:
        final_state = next_state

    if "title" in changes:
        row.title = changes["title"]
    if "description" in changes:
        row.description = changes["description"]
    row.state = RequirementState(final_state)
    if row.origin.value == "ai" and touched:
        row.origin = RequirementOrigin.USER

    db.commit()
    db.refresh(row)
    source_links = _load_source_links(db, [row.id])
    return RequirementSummary.from_model(row, source_links.get(row.id, []))


def delete_requirement(db: Session, user_id: str, project_id: str, req_id: str) -> None:
    row = db.execute(
        select(Requirement).where(
            Requirement.id == req_id,
            Requirement.project_id == project_id,
            Requirement.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Requirement not found")
    db.delete(row)
    db.commit()
