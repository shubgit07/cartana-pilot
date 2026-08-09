"""Tests for the Tasks module.

Covers list, create, get (detail), update (state + relink), delete, 404s,
and requirement validation.
"""
from __future__ import annotations

from app.db.models import Task, TaskOrigin, TaskState
from tests.conftest import seed_project
from tests.test_requirements import _seed_requirement

TASK_KEYS = {
    "id", "projectId", "requirementId", "requirementTitle", "title",
    "description", "origin", "state", "sourceLinks", "createdAt", "updatedAt",
}


def _seed_task(db, project, *, title="Build the API", description="Create REST endpoints", origin=TaskOrigin.AI, state=TaskState.SUGGESTED, user_id=None, requirement_id=None):
    task = Task(
        project_id=project.id,
        user_id=user_id or project.user_id,
        title=title,
        description=description,
        origin=origin,
        state=state,
        requirement_id=requirement_id,
        dedupe_key="task-key",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_list_empty(client, db_session):
    project = seed_project(db_session)
    resp = client.get(f"/projects/{project.id}/tasks")
    assert resp.status_code == 200
    assert resp.json() == {"tasks": []}


def test_list_returns_tasks(client, db_session):
    project = seed_project(db_session)
    _seed_task(db_session, project, title="Build the API")
    _seed_task(db_session, project, title="Design the database")
    resp = client.get(f"/projects/{project.id}/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tasks"]) == 2
    for item in data["tasks"]:
        assert set(item.keys()) == TASK_KEYS


def test_create_task(client, db_session):
    project = seed_project(db_session)
    resp = client.post(f"/projects/{project.id}/tasks", json={"title": "Deploy to staging", "description": "Set up CI/CD"})
    assert resp.status_code == 201
    data = resp.json()["task"]
    assert data["title"] == "Deploy to staging"
    assert data["origin"] == "user"
    assert data["state"] == "accepted"


def test_create_task_with_requirement_link(client, db_session):
    project = seed_project(db_session)
    req = _seed_requirement(db_session, project)
    resp = client.post(
        f"/projects/{project.id}/tasks",
        json={"title": "Implement SSO", "requirementId": req.id},
    )
    assert resp.status_code == 201
    data = resp.json()["task"]
    assert data["requirementId"] == req.id
    assert data["requirementTitle"] == req.title


def test_create_task_invalid_requirement(client, db_session):
    project = seed_project(db_session)
    resp = client.post(
        f"/projects/{project.id}/tasks",
        json={"title": "Implement X", "requirementId": "nonexistent"},
    )
    assert resp.status_code == 404


def test_get_task_detail(client, db_session):
    project = seed_project(db_session)
    task = _seed_task(db_session, project)
    resp = client.get(f"/projects/{project.id}/tasks/{task.id}")
    assert resp.status_code == 200
    data = resp.json()["task"]
    assert "chunkLinks" in data


def test_update_task_relink(client, db_session):
    project = seed_project(db_session)
    task = _seed_task(db_session, project)
    req = _seed_requirement(db_session, project, title="Must support auth")
    resp = client.patch(f"/projects/{project.id}/tasks/{task.id}", json={"requirementId": req.id})
    assert resp.status_code == 200
    data = resp.json()["task"]
    assert data["requirementId"] == req.id


def test_update_task_state_transitions(client, db_session):
    project = seed_project(db_session)
    task = _seed_task(db_session, project, origin=TaskOrigin.AI, state=TaskState.SUGGESTED)
    resp = client.patch(f"/projects/{project.id}/tasks/{task.id}", json={"state": "accepted"})
    assert resp.status_code == 200
    data = resp.json()["task"]
    assert data["state"] == "accepted"
    assert data["origin"] == "user"


def test_delete_task(client, db_session):
    project = seed_project(db_session)
    task = _seed_task(db_session, project)
    resp = client.delete(f"/projects/{project.id}/tasks/{task.id}")
    assert resp.status_code == 204
