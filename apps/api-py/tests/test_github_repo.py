"""GitHub public-repo Codebase Index tests (connect / resync / disconnect).

HTTP to api.github.com is faked: no network, no token required.
"""
from __future__ import annotations

import base64
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import CodeChunk, RepositoryConnection, RepositoryFile, RepositorySnapshot
from app.providers import github_provider
from app.providers.github_provider import (
    CommitItem,
    PullItem,
    RepoFetchResult,
    RepoFile,
    RepoMeta,
    ensure_public,
    fetch_repo_files,
    parse_repo_url,
)
from tests.conftest import seed_project


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _fake_get(routes: dict[str, Any]):
    def handler(url: str, **kwargs: Any):
        if url in routes:
            payload = routes[url]
        else:
            # Query-string call, e.g. .../trees/<sha>?recursive=1.
            payload = None
            for prefix, candidate in routes.items():
                if url.startswith(prefix + "?"):
                    payload = candidate
                    break
            if payload is None:
                raise AssertionError(f"unexpected GitHub URL: {url}")

        class FakeResponse:
            status_code = 200
            text = ""

            def json(self) -> Any:
                return payload

        return FakeResponse()

    return handler


# ---- URL parsing ----


def test_parse_repo_url_accepts_variants() -> None:
    assert parse_repo_url("https://github.com/acme/shop") == ("acme", "shop")
    assert parse_repo_url("https://github.com/acme/shop.git") == ("acme", "shop")
    assert parse_repo_url("https://github.com/acme/shop/tree/main") == ("acme", "shop")
    assert parse_repo_url("acme/shop") == ("acme", "shop")


def test_parse_repo_url_rejects_non_github() -> None:
    with pytest.raises(Exception):
        parse_repo_url("https://gitlab.com/acme/shop")
    with pytest.raises(Exception):
        parse_repo_url("not a url at all !!")


# ---- visibility gate ----


def test_ensure_public_refuses_private_repos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        github_provider.httpx,
        "get",
        _fake_get({
            "https://api.github.com/repos/acme/secret": {
                "name": "secret",
                "full_name": "acme/secret",
                "private": True,
                "default_branch": "main",
                "clone_url": "https://github.com/acme/secret.git",
                "owner": {"login": "acme"},
            },
        }),
    )
    with pytest.raises(Exception, match="public"):
        ensure_public("acme", "secret")


# ---- file fetch + pre-filter ----


def test_fetch_repo_files_filters_junk_and_decodes(monkeypatch: pytest.MonkeyPatch) -> None:
    code = "def hello():\n    return 1\n"
    monkeypatch.setattr(
        github_provider.httpx,
        "get",
        _fake_get({
            "https://api.github.com/repos/acme/shop": {
                "name": "shop",
                "full_name": "acme/shop",
                "private": False,
                "default_branch": "main",
                "clone_url": "https://github.com/acme/shop.git",
                "owner": {"login": "acme"},
            },
            "https://api.github.com/repos/acme/shop/commits/main": {"sha": "abc123"},
            "https://api.github.com/repos/acme/shop/git/trees/abc123": {
                "tree": [
                    {"type": "blob", "path": "app/main.py", "sha": "b1", "size": 40},
                    {"type": "blob", "path": "node_modules/dep/index.js", "sha": "b2", "size": 40},
                    {"type": "blob", "path": "logo.png", "sha": "b3", "size": 40},
                    {"type": "blob", "path": "huge.py", "sha": "b4", "size": 999_999_999},
                ]
            },
            "https://api.github.com/repos/acme/shop/git/blobs/b1": {
                "encoding": "base64",
                "content": _b64(code),
            },
        }),
    )
    result = fetch_repo_files("acme", "shop")

    assert result.commit_sha == "abc123"
    assert result.ref_name == "main"
    assert [(f.path, f.content) for f in result.files] == [("app/main.py", code)]
    assert any("node_modules" in s for s in result.skipped)
    assert any("logo.png" in s for s in result.skipped)
    assert any("huge.py" in s for s in result.skipped)


# ---- connect / resync / disconnect routes ----


def _stub_fetch(monkeypatch: pytest.MonkeyPatch, sha: str = "abc123") -> None:
    monkeypatch.setattr(
        github_provider,
        "ensure_public",
        lambda owner, repo: RepoMeta(
            owner=owner,
            repo=repo,
            default_branch="main",
            private=False,
            display_name=f"{owner}/{repo}",
            clone_url=f"https://github.com/{owner}/{repo}.git",
        ),
    )
    monkeypatch.setattr(
        github_provider,
        "fetch_repo_files",
        lambda owner, repo, ref=None: RepoFetchResult(
            files=[RepoFile(path="app/main.py", content="def hello():\n    return 1\n")],
            commit_sha=sha,
            ref_name="main",
        ),
    )
    monkeypatch.setattr(
        github_provider, "get_branch_head_sha", lambda owner, repo, branch: sha
    )


def test_connect_builds_codebase_index(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = seed_project(db_session)
    _stub_fetch(monkeypatch)

    response = client.post(
        f"/projects/{project.id}/repository/connect",
        json={"repoUrl": "https://github.com/acme/shop"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["repoUrl"] == "https://github.com/acme/shop"
    assert body["displayName"] == "acme/shop"
    assert body["commitSha"] == "abc123"
    assert body["filesIndexed"] == 1
    assert body["chunksCreated"] >= 1

    status = client.get(f"/projects/{project.id}/repository/status").json()
    assert status["connected"] is True
    assert status["repoUrl"] == "https://github.com/acme/shop"
    assert status["commitSha"] == "abc123"
    assert status["indexedFilesCount"] == 1


def test_connect_rejects_private_repos(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = seed_project(db_session)
    monkeypatch.setattr(
        github_provider, "parse_repo_url", lambda url: ("acme", "secret")
    )
    monkeypatch.setattr(
        github_provider,
        "ensure_public",
        lambda owner, repo: (_ for _ in ()).throw(
            __import__("app.core.errors", fromlist=["ValidationError"]).ValidationError(
                "Only public repositories are supported right now"
            )
        ),
    )

    response = client.post(
        f"/projects/{project.id}/repository/connect",
        json={"repoUrl": "https://github.com/acme/secret"},
    )

    assert response.status_code == 400
    assert "public" in response.json()["error"]["message"]


def test_resync_is_noop_when_up_to_date(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = seed_project(db_session)
    _stub_fetch(monkeypatch)
    assert (
        client.post(
            f"/projects/{project.id}/repository/connect",
            json={"repoUrl": "https://github.com/acme/shop"},
        ).status_code
        == 200
    )

    body = client.post(f"/projects/{project.id}/repository/resync").json()

    assert body["upToDate"] is True
    assert body["filesIndexed"] == 0
    assert body["commitSha"] == "abc123"


def test_resync_indexes_new_head(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = seed_project(db_session)
    _stub_fetch(monkeypatch, sha="abc123")
    assert (
        client.post(
            f"/projects/{project.id}/repository/connect",
            json={"repoUrl": "https://github.com/acme/shop"},
        ).status_code
        == 200
    )

    _stub_fetch(monkeypatch, sha="def456")
    body = client.post(f"/projects/{project.id}/repository/resync").json()

    assert body["upToDate"] is False
    assert body["commitSha"] == "def456"
    assert client.get(f"/projects/{project.id}/repository/status").json()["commitSha"] == "def456"


def test_disconnect_purges_codebase_index(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = seed_project(db_session)
    _stub_fetch(monkeypatch)
    assert (
        client.post(
            f"/projects/{project.id}/repository/connect",
            json={"repoUrl": "https://github.com/acme/shop"},
        ).status_code
        == 200
    )
    assert db_session.query(CodeChunk).count() >= 1

    assert client.delete(f"/projects/{project.id}/repository/connection").status_code == 204

    assert db_session.query(RepositoryConnection).count() == 0
    assert db_session.query(RepositorySnapshot).count() == 0
    assert db_session.query(RepositoryFile).count() == 0
    assert db_session.query(CodeChunk).count() == 0
    assert client.get(f"/projects/{project.id}/repository/status").json()["connected"] is False


def test_pulls_and_commits_list(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = seed_project(db_session)
    _stub_fetch(monkeypatch)
    assert (
        client.post(
            f"/projects/{project.id}/repository/connect",
            json={"repoUrl": "https://github.com/acme/shop"},
        ).status_code
        == 200
    )
    monkeypatch.setattr(
        github_provider,
        "list_pulls",
        lambda owner, repo, state="open", limit=20: [
            PullItem(
                number=7, title="Add checkout", head_sha="def456",
                base_branch="main", updated_at=None,
                url="https://github.com/acme/shop/pull/7", author="octo",
            )
        ],
    )
    monkeypatch.setattr(
        github_provider,
        "list_commits",
        lambda owner, repo, branch, limit=10: [
            CommitItem(
                sha="abc123", message="init", author="octo",
                date=None, url="https://github.com/acme/shop/commit/abc123",
            )
        ],
    )

    pulls = client.get(f"/projects/{project.id}/repository/pulls").json()["pulls"]
    assert pulls[0]["number"] == 7
    assert pulls[0]["headSha"] == "def456"

    commits = client.get(f"/projects/{project.id}/repository/commits").json()["commits"]
    assert commits[0]["sha"] == "abc123"
