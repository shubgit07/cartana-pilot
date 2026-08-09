"""Tests for the Requirements module.

Covers list, get (detail), update (state transitions + origin flip), delete,
404s, and ownership isolation. Uses the shared in-memory SQLite fixtures.
"""
from __future__ import annotations

from app.db.models import (
    Requirement,
    RequirementChunk,
    RequirementOrigin,
    RequirementState,
)
from tests.conftest import OTHER_USER_ID, seed_project, seed_source

REQUIREMENT_KEYS = {
    "id", "projectId", "title", "description", "origin", "state",
    "sourceLinks", "createdAt", "updatedAt",
}


def _seed_requirement(db, project, *, title="Must support SSO", description="The system must support SSO via SAML 2.0", origin=RequirementOrigin.AI, state=RequirementState.SUGGESTED, user_id=None, source=None):
    req = Requirement(
        project_id=project.id,
        user_id=user_id or project.user_id,
        title=title,
        description=description,
        origin=origin,
        state=state,
        dedupe_key="test-key",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    if source:
        chunk = source.chunks[0] if source.chunks else None
        if chunk is None:
            from app.db.models import Chunk
            chunk = Chunk(source_id=source.id, position=0, text="test chunk text")
            db.add(chunk)
            db.commit()
            db.refresh(chunk)
        db.add(RequirementChunk(requirement_id=req.id, chunk_id=chunk.id))
        db.commit()
    return req


def test_list_empty(client, db_session):
    project = seed_project(db_session)
    resp = client.get(f"/projects/{project.id}/requirements")
    assert resp.status_code == 200
    assert resp.json() == {"requirements": []}


def test_list_returns_requirements(client, db_session):
    project = seed_project(db_session)
    _seed_requirement(db_session, project, title="Must support SSO")
    _seed_requirement(db_session, project, title="Shall handle errors")
    resp = client.get(f"/projects/{project.id}/requirements")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["requirements"]) == 2
    for item in data["requirements"]:
        assert set(item.keys()) == REQUIREMENT_KEYS


def test_get_detail(client, db_session):
    project = seed_project(db_session)
    source = seed_source(db_session, project, chunks=1)
    req = _seed_requirement(db_session, project, source=source)
    resp = client.get(f"/projects/{project.id}/requirements/{req.id}")
    assert resp.status_code == 200
    data = resp.json()["requirement"]
    assert "chunkLinks" in data
    assert len(data["chunkLinks"]) == 1


def test_get_404(client, db_session):
    project = seed_project(db_session)
    resp = client.get(f"/projects/{project.id}/requirements/nonexistent")
    assert resp.status_code == 404


def test_update_state_transitions(client, db_session):
    project = seed_project(db_session)
    req = _seed_requirement(db_session, project, origin=RequirementOrigin.AI, state=RequirementState.SUGGESTED)

    resp = client.patch(f"/projects/{project.id}/requirements/{req.id}", json={"state": "accepted"})
    assert resp.status_code == 200
    data = resp.json()["requirement"]
    assert data["state"] == "accepted"
    assert data["origin"] == "user"


def test_update_title_flips_to_edited(client, db_session):
    project = seed_project(db_session)
    req = _seed_requirement(db_session, project, origin=RequirementOrigin.AI, state=RequirementState.SUGGESTED)

    resp = client.patch(f"/projects/{project.id}/requirements/{req.id}", json={"title": "Updated title here"})
    assert resp.status_code == 200
    data = resp.json()["requirement"]
    assert data["state"] == "edited"
    assert data["origin"] == "user"
    assert data["title"] == "Updated title here"


def test_update_partial_description(client, db_session):
    project = seed_project(db_session)
    req = _seed_requirement(db_session, project, origin=RequirementOrigin.USER, state=RequirementState.ACCEPTED)

    resp = client.patch(f"/projects/{project.id}/requirements/{req.id}", json={"description": "New desc"})
    assert resp.status_code == 200
    data = resp.json()["requirement"]
    assert data["description"] == "New desc"


def test_delete(client, db_session):
    project = seed_project(db_session)
    req = _seed_requirement(db_session, project)
    resp = client.delete(f"/projects/{project.id}/requirements/{req.id}")
    assert resp.status_code == 204
    resp2 = client.get(f"/projects/{project.id}/requirements/{req.id}")
    assert resp2.status_code == 404


def test_other_user_isolated(client, db_session):
    project = seed_project(db_session)
    _seed_requirement(db_session, project, user_id=OTHER_USER_ID)
    resp = client.get(f"/projects/{project.id}/requirements")
    assert resp.status_code == 200
    assert len(resp.json()["requirements"]) == 0
