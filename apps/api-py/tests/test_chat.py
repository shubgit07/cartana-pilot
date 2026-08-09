"""Tests for the Chat module.

The chat LLM is intentionally not wired up, so every valid request is rejected
with HTTP 501 and a clear error. These tests cover the endpoint contract:
ownership check (404), request validation (422), and the unwired-chat error.
"""
from __future__ import annotations

from tests.conftest import seed_project


def test_chat_project_not_found(client, db_session):
    resp = client.post(
        "/projects/nonexistent/chat",
        json={"question": "What is this project about?"},
    )
    assert resp.status_code == 404


def test_chat_validation_empty_question(client, db_session):
    project = seed_project(db_session)
    resp = client.post(f"/projects/{project.id}/chat", json={"question": ""})
    assert resp.status_code == 422


def test_chat_returns_501_when_llm_not_wired(client, db_session):
    project = seed_project(db_session)
    resp = client.post(
        f"/projects/{project.id}/chat",
        json={"question": "What does this project do?"},
    )
    assert resp.status_code == 501
    data = resp.json()
    assert data["error"]["code"] == "chat_not_wired"
    assert data["error"]["message"] == "LLM is not wired up"


def test_chat_with_history_returns_501(client, db_session):
    project = seed_project(db_session)
    resp = client.post(
        f"/projects/{project.id}/chat",
        json={
            "question": "Tell me more",
            "history": [
                {"role": "user", "content": "What is this?"},
                {"role": "assistant", "content": "It is a project."},
            ],
        },
    )
    assert resp.status_code == 501
