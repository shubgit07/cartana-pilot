"""Tests for the Chat module.

Covers the chat endpoint with stub provider (no LLM credentials needed).
The stub returns retrieval-only answers from pgvector search, but since
SQLite tests don't have pgvector, we test the service-level contract:
ownership check, response shape, and 404 for missing projects.
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


def test_chat_response_shape(client, db_session):
    """With no chunks/embeddings, the stub returns a 'no passages' answer."""
    project = seed_project(db_session)
    resp = client.post(
        f"/projects/{project.id}/chat",
        json={"question": "What does this project do?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    msg = data["message"]
    assert msg["role"] == "assistant"
    assert "content" in msg
    assert "createdAt" in msg


def test_chat_with_history(client, db_session):
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
    assert resp.status_code == 200
