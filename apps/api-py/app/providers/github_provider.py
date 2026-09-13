"""GitHub public-repo fetch layer for the Codebase Index.

Design notes:
- MVP covers **public repositories only**: no OAuth, no GitHub App. Reads go
  through ``api.github.com`` (anonymous 60 req/hr; a server-side ``GITHUB_TOKEN``
  lifts this to 5,000/hr — public data only).
- Pure fetch layer: no DB access. The caller (``repo_index_service``) owns
  persistence, chunking, and the authoritative ignore/size gates. This module
  applies a light pre-filter so we never download megabytes of ``node_modules``
  just to discard them.
- Raw code is never stored: blobs are decoded in memory and handed to the
  sync pipeline, which keeps chunks + vectors only.
"""
from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx

from app.config import get_settings
from app.core.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

_API = "https://api.github.com"
_TIMEOUT = 20.0

# Keep downloads bounded: worst case 500 files x 150KB mirrors the sync caps.
MAX_FILES = 500
MAX_FILE_BYTES = 150_000

# Pre-filter top-level dependency / build / VCS directories before download.
_SKIP_DIRS = frozenset({
    "node_modules", "dist", "build", ".next", ".nuxt", "vendor",
    ".git", "__pycache__", ".venv", "venv", ".tox", ".eggs",
    "coverage", ".nyc_output", "target", "bin", "obj", "out",
})
# Pre-filter binary / generated / lockfile extensions before download.
_SKIP_EXTS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp",
    ".mp4", ".mp3", ".wav", ".ogg", ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll", ".so",
    ".bin", ".dat", ".db", ".sqlite", ".pyc", ".pyo", ".class",
    ".min.js", ".min.css", ".map", ".lock",
})
_SKIP_FILES = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Pipfile.lock", "Gemfile.lock", "Cargo.lock", "composer.lock",
    ".DS_Store", "Thumbs.db",
})

_URL_RE = re.compile(r"^github\.com/([^/]+)/([^/]+?)(?:\.git)?$", re.IGNORECASE)


@dataclass
class RepoMeta:
    owner: str
    repo: str
    default_branch: str
    private: bool
    display_name: str
    clone_url: str


@dataclass
class RepoFile:
    path: str
    content: str


@dataclass
class RepoFetchResult:
    files: list[RepoFile] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    commit_sha: str = ""
    ref_name: str = ""


@dataclass
class PullItem:
    number: int
    title: str
    head_sha: str
    base_branch: str
    updated_at: str | None
    url: str
    author: str | None


@dataclass
class CommitItem:
    sha: str
    message: str
    author: str | None
    date: str | None
    url: str


def parse_repo_url(raw: str) -> tuple[str, str]:
    """Accept ``https://github.com/o/r[.git][/...]`` or ``o/r`` shorthand."""
    text = (raw or "").strip().rstrip("/")
    if not text:
        raise ValidationError("Repository URL is required")
    if "://" in text:
        parts = urlsplit(text)
        if parts.hostname not in ("github.com", "www.github.com"):
            raise ValidationError("Only github.com repository URLs are supported")
        # Drop trailing sub-paths such as /tree/<branch> or /pull/123.
        segments = [s for s in parts.path.split("/") if s]
        if len(segments) < 2:
            raise ValidationError("Could not find owner/repository in that URL")
        text = f"github.com/{segments[0]}/{segments[1]}"
    elif re.fullmatch(r"[^/\s]+/[^/\s]+", text):
        text = f"github.com/{text}"
    match = _URL_RE.match(text.removesuffix(".git"))
    if not match:
        raise ValidationError("Use a github.com URL like https://github.com/owner/repo")
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    if not owner or not repo:
        raise ValidationError("Use a github.com URL like https://github.com/owner/repo")
    return owner, repo


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Cartana-Codebase-Index",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = (get_settings().github_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def _get(path: str, params: dict | None = None) -> httpx.Response:
    try:
        response = httpx.get(f"{_API}{path}", headers=_headers(), params=params, timeout=_TIMEOUT)
    except Exception as exc:
        raise ValidationError(f"Could not reach GitHub: {exc}") from exc
    if response.status_code == 404:
        raise NotFoundError("Repository not found on GitHub")
    if response.status_code == 403 and "rate limit" in response.text.lower():
        raise ValidationError("GitHub rate limit reached — try again in a few minutes")
    if response.status_code in (401, 403, 422):
        raise ValidationError(f"GitHub rejected the request (HTTP {response.status_code})")
    if response.status_code != 200:
        raise ValidationError(f"GitHub request failed (HTTP {response.status_code})")
    return response


def get_repo(owner: str, repo: str) -> RepoMeta:
    data = _get(f"/repos/{owner}/{repo}").json()
    return RepoMeta(
        owner=data.get("owner", {}).get("login", owner),
        repo=data.get("name", repo),
        default_branch=data.get("default_branch") or "main",
        private=bool(data.get("private", False)),
        display_name=data.get("full_name") or f"{owner}/{repo}",
        clone_url=data.get("clone_url") or f"https://github.com/{owner}/{repo}.git",
    )


def ensure_public(owner: str, repo: str) -> RepoMeta:
    """Fetch repo metadata and refuse private repositories (MVP rule)."""
    meta = get_repo(owner, repo)
    if meta.private:
        raise ValidationError("Only public repositories are supported right now")
    return meta


def get_branch_head_sha(owner: str, repo: str, branch: str) -> str:
    data = _get(f"/repos/{owner}/{repo}/commits/{branch}").json()
    sha = data.get("sha") or ""
    if not sha:
        raise ValidationError(f"Branch {branch!r} not found")
    return sha


def _prefiltered(path: str, size: int | None) -> str | None:
    """Return a skip reason, or None when the blob is worth downloading."""
    lowered = path.lower()
    top = lowered.split("/", 1)[0]
    if top in _SKIP_DIRS or "/node_modules/" in lowered:
        return "dependency/build output"
    filename = lowered.rsplit("/", 1)[-1]
    if filename in _SKIP_FILES:
        return "lockfile/system file"
    for ext in _SKIP_EXTS:
        if lowered.endswith(ext):
            return "binary/generated asset"
    if size is not None and size > MAX_FILE_BYTES:
        return f"oversize ({size}B)"
    return None


def fetch_repo_files(owner: str, repo: str, ref: str | None = None) -> RepoFetchResult:
    """Download a filtered file set for one ref (branch name or SHA)."""
    meta = ensure_public(owner, repo)
    branch = ref or meta.default_branch
    head_sha = get_branch_head_sha(owner, repo, branch)
    tree = _get(f"/repos/{owner}/{repo}/git/trees/{head_sha}", params={"recursive": "1"}).json()
    entries = [t for t in tree.get("tree", []) if t.get("type") == "blob"]

    result = RepoFetchResult(commit_sha=head_sha, ref_name=branch)
    for entry in entries:
        path = entry.get("path") or ""
        if len(result.files) >= MAX_FILES:
            result.skipped.append(f"... and more files over the {MAX_FILES} cap")
            break
        reason = _prefiltered(path, entry.get("size"))
        if reason:
            result.skipped.append(f"{path} ({reason})")
            continue
        blob = _get(f"/repos/{owner}/{repo}/git/blobs/{entry['sha']}").json()
        if blob.get("encoding") != "base64" or not blob.get("content"):
            result.skipped.append(f"{path} (unreadable)")
            continue
        try:
            text = base64.b64decode(blob["content"]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            result.skipped.append(f"{path} (binary)")
            continue
        if "\x00" in text:
            result.skipped.append(f"{path} (binary)")
            continue
        if len(text.encode("utf-8")) > MAX_FILE_BYTES:
            result.skipped.append(f"{path} (oversize)")
            continue
        result.files.append(RepoFile(path=path, content=text))
    logger.info(
        "github:fetched (repo=%s/%s, ref=%s, files=%d, skipped=%d)",
        owner, repo, branch, len(result.files), len(result.skipped),
    )
    return result


def list_pulls(owner: str, repo: str, state: str = "open", limit: int = 20) -> list[PullItem]:
    ensure_public(owner, repo)
    if state not in ("open", "closed", "all"):
        state = "open"
    data = _get(
        f"/repos/{owner}/{repo}/pulls",
        params={"state": state, "per_page": max(1, min(limit, 50))},
    ).json()
    items = []
    for pr in data:
        items.append(PullItem(
            number=pr.get("number", 0),
            title=pr.get("title") or "",
            head_sha=(pr.get("head") or {}).get("sha") or "",
            base_branch=(pr.get("base") or {}).get("ref") or "",
            updated_at=pr.get("updated_at"),
            url=pr.get("html_url") or "",
            author=(pr.get("user") or {}).get("login"),
        ))
    return items


def list_commits(owner: str, repo: str, branch: str, limit: int = 10) -> list[CommitItem]:
    ensure_public(owner, repo)
    data = _get(
        f"/repos/{owner}/{repo}/commits",
        params={"sha": branch, "per_page": max(1, min(limit, 30))},
    ).json()
    items = []
    for commit in data:
        inner = commit.get("commit") or {}
        items.append(CommitItem(
            sha=commit.get("sha") or "",
            message=(inner.get("message") or "").split("\n", 1)[0],
            author=((inner.get("author") or {}).get("name")),
            date=(inner.get("author") or {}).get("date"),
            url=commit.get("html_url") or "",
        ))
    return items


def fetch_pr_diff(owner: str, repo: str, number: int) -> str:
    """Download a PR unified diff (public repos need no auth)."""
    ensure_public(owner, repo)
    try:
        response = httpx.get(
            f"{_API}/repos/{owner}/{repo}/pulls/{number}",
            headers=_headers({"Accept": "application/vnd.github.diff"}),
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        raise ValidationError(f"Could not download PR diff: {exc}") from exc
    if response.status_code != 200:
        raise ValidationError(f"Could not download PR diff (HTTP {response.status_code})")
    return response.text


def fetch_commit_patch(owner: str, repo: str, sha: str) -> str:
    """Download a commit patch (public repos need no auth)."""
    ensure_public(owner, repo)
    try:
        response = httpx.get(
            f"{_API}/repos/{owner}/{repo}/commits/{sha}",
            headers=_headers({"Accept": "application/vnd.github.patch"}),
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        raise ValidationError(f"Could not download commit patch: {exc}") from exc
    if response.status_code != 200:
        raise ValidationError(f"Could not download commit patch (HTTP {response.status_code})")
    return response.text
