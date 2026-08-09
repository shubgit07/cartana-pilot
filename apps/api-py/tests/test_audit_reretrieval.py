"""Tests for B2 — coverage-audit candidate retrieval + re-retrieval pass.

Covers the embedding cosine retrieval (fail-loud on embed errors) and the
confidence-triggered re-retrieval pass in ``audit_service``.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import LLMServiceError
from app.db.models import (
    CoverageLink,
    CoverageStatus,
    Requirement,
    RequirementOrigin,
    RequirementState,
    Task,
    TaskOrigin,
    TaskState,
)
from app.providers.ai_provider import (
    AIAuditCoverageOutput,
    CoverageJudgment,
)
from tests.conftest import seed_project

# ---- Helpers ----


def _make_task(db, project, title: str) -> Task:
    task = Task(
        project_id=project.id,
        user_id=project.user_id,
        title=title,
        description=f"Implement {title}",
        origin=TaskOrigin.USER,
        state=TaskState.ACCEPTED,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _cosine_similarity(a, b):
    return sum(x * y for x, y in zip(a, b))


class ScriptedEmbeddingProvider:
    """Returns vectors for [req_text, task1, ..., taskN] from a callable."""

    id = "scripted"
    dim = 8

    def __init__(self, vector_fn):
        self._vector_fn = vector_fn

    def embed(self, texts):
        return [self._vector_fn(i, t) for i, t in enumerate(texts)]


class ScriptedAIProvider:
    """Judges each candidate task independently; covering task -> covered, else missing."""

    parallel_audit = False

    def __init__(self, covering_title: str):
        self._covering = covering_title

    def audit_coverage(self, input):
        judgments = [
            CoverageJudgment(
                status="covered" if c["title"] == self._covering else "missing",
                rationale="scripted",
            )
            for c in input.candidateTasks
        ]
        return AIAuditCoverageOutput(judgments=judgments)

    def risk_summary(self, input):
        return SimpleNamespace(summary="scripted")


def _run_audit_with(
    db,
    user_id: str,
    project_id: str,
    *,
    ai_provider,
    embedding_provider,
):
    import app.api.services.audit_service as svc

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(svc, "get_ai_provider", lambda: ai_provider)
    monkeypatch.setattr(svc, "get_embedding_provider", lambda: embedding_provider)
    try:
        run_id = svc.run_audit(db, user_id, project_id)
    finally:
        monkeypatch.undo()
    return run_id


# ---- Candidate retrieval ----


def test_select_candidate_tasks_returns_most_similar(db_session, monkeypatch):
    import app.api.services.audit_service as svc

    project = seed_project(db_session)
    _make_task(db_session, project, "User authentication")
    covering = _make_task(db_session, project, "Account login flow")
    _make_task(db_session, project, "Email notifications")

    def vector_fn(i, text):
        # Requirement + task that shares its wording align; other tasks are orthogonal.
        return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] if i == 0 else (
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            if "Account login flow" in text
            else [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        )

    monkeypatch.setattr(
        svc,
        "get_embedding_provider",
        lambda: ScriptedEmbeddingProvider(vector_fn),
    )
    selected = svc._select_candidate_tasks(
        "Account login flow", [t for t in db_session.query(Task).all()], top_k=2
    )
    assert selected[0].title == covering.title


def test_select_candidate_tasks_fails_loudly_on_embed_error(db_session, monkeypatch):
    import app.api.services.audit_service as svc

    project = seed_project(db_session)
    for i in range(6):
        _make_task(db_session, project, f"Some task {i}")

    class BoomEmbeddings:
        id = "boom"
        dim = 8

        def embed(self, texts):
            raise RuntimeError("embed api down")

    monkeypatch.setattr(svc, "get_embedding_provider", lambda: BoomEmbeddings())
    with pytest.raises(LLMServiceError, match="Embedding unavailable"):
        svc._select_candidate_tasks(
            "Requirement text", list(db_session.query(Task).all()), top_k=5
        )


def test_select_candidate_tasks_returns_all_when_at_or_below_top_k(db_session, monkeypatch):
    import app.api.services.audit_service as svc

    project = seed_project(db_session)
    _make_task(db_session, project, "Task one")
    _make_task(db_session, project, "Task two")

    monkeypatch.setattr(
        svc,
        "get_embedding_provider",
        lambda: ScriptedEmbeddingProvider(
            lambda i, t: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ),
    )
    tasks = list(db_session.query(Task).all())
    assert svc._select_candidate_tasks("x", tasks, top_k=5) == tasks


# ---- Re-retrieval pass (run_audit) ----


def test_reretrieval_rescues_requirement_when_covering_task_ranks_6_to_10(db_session):
    """A requirement judged missing on top-5 is re-searched at top_k=10 and rescued."""

    project = seed_project(db_session)
    req = Requirement(
        project_id=project.id,
        user_id=project.user_id,
        title="Must support SSO",
        description="Users must be able to sign in with single sign-on.",
        origin=RequirementOrigin.AI,
        state=RequirementState.ACCEPTED,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    decoy_titles = [f"Decoy feature {i}" for i in range(1, 6)]
    covering_title = "Identity provider integration"
    unrelated_titles = ["Billing report", "Export CSV", "Dark mode", "Keyboard nav"]

    tasks = []
    for title in decoy_titles + unrelated_titles:
        tasks.append(_make_task(db_session, project, title))
    covering = _make_task(db_session, project, covering_title)

    # req_vec aligns 0.9 with decoys (ranks 1-5), 0.8 with the covering task
    # (rank 6), and near-zero with the unrelated tasks (ranks 7-10).
    task_titles = [t.title for t in tasks + [covering]]
    all_titles = [req.title, *task_titles]

    def vector_fn(i, text):
        if i == 0:
            return [1.0] * 8
        title = all_titles[i]
        if title in decoy_titles:
            return [0.9] * 8
        if title == covering_title:
            return [0.8] * 8
        return [0.05] * 8

    run_id = _run_audit_with(
        db_session,
        project.user_id,
        project.id,
        ai_provider=ScriptedAIProvider(covering_title),
        embedding_provider=ScriptedEmbeddingProvider(vector_fn),
    )
    assert run_id

    links = db_session.query(CoverageLink).filter(
        CoverageLink.requirement_id == req.id
    ).all()
    assert any(link.task_id == covering.id for link in links)


def test_reretrieval_does_not_rescue_absent_task(db_session):
    """No rescue when the covering task does not exist at all."""
    project = seed_project(db_session)
    req = Requirement(
        project_id=project.id,
        user_id=project.user_id,
        title="Must support SSO",
        description="Users must be able to sign in with single sign-on.",
        origin=RequirementOrigin.AI,
        state=RequirementState.ACCEPTED,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    for title in ["Decoy feature 1", "Decoy feature 2", "Decoy feature 3"]:
        _make_task(db_session, project, title)

    def vector_fn(i, text):
        return [1.0] * 8 if i == 0 else [0.9] * 8

    run_id = _run_audit_with(
        db_session,
        project.user_id,
        project.id,
        ai_provider=ScriptedAIProvider("Identity provider integration"),
        embedding_provider=ScriptedEmbeddingProvider(vector_fn),
    )
    assert run_id

    links = db_session.query(CoverageLink).filter(
        CoverageLink.requirement_id == req.id
    ).all()
    assert links, "top-5 candidates still produce links (all missing)"
    assert all(link.status == CoverageStatus.MISSING for link in links)
