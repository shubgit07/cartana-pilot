"""Phase 2 pipeline driver.

Runs a real document through the full Cartana ingestion + audit pipeline and
reports per-stage wall times vs the <40 s target.

Usage:
    .venv\\Scripts\\python.exe scripts/run_pipeline.py <path-to-doc>

Reads config from ``.env`` (LLM_PROVIDER=routing → Gemini extraction/audit,
Groq chat; stub embeddings; local Postgres + Redis). Creates a fresh project
and source row, executes every pipeline stage synchronously, promotes AI
suggestions to accepted, runs the coverage audit, and prints a report.

The created rows are intentionally left in the database so results can be
inspected via the API afterwards.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from sqlalchemy import select

from app.api.services.audit_service import promote_suggestions_to_accepted, run_audit
from app.config import get_settings
from app.db.models import (
    AuditFinding,
    CoverageLink,
    Project,
    Requirement,
    Source,
    SourceKind,
    SourceStatus,
    Task,
    User,
)
from app.db.session import SessionLocal
from app.providers.storage_provider import build_storage_key, get_storage
from app.workers.arq_worker import (
    execute_chunk_stage,
    execute_embed_stage,
    execute_extract_requirements_stage,
    execute_extract_tasks_stage,
    execute_ingest_stage,
)

TARGET_SECONDS = 40.0


def _timed(label: str, fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  {label:<28} {elapsed_ms:>9.1f} ms")
    return result, elapsed_ms


def _ensure_dev_user(db) -> User:
    settings = get_settings()
    user = db.execute(select(User).where(User.id == settings.dev_user_id)).scalar_one_or_none()
    if user is None:
        user = User(
            id=settings.dev_user_id,
            email=settings.dev_user_email,
            name=settings.dev_user_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[setup] created dev user {user.id}")
    return user


def main(path: str) -> None:
    file = Path(path)
    if not file.is_file():
        raise SystemExit(f"File not found: {path}")
    data = file.read_bytes()
    print(f"[setup] input: {file.name} ({len(data)} bytes)")

    db = SessionLocal()
    try:
        user = _ensure_dev_user(db)

        project = Project(
            user_id=user.id,
            name=f"Pipeline test {file.stem} ({time.strftime('%Y-%m-%d %H:%M:%S')})",
            description="Created by scripts/run_pipeline.py",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"[setup] project: {project.id} ({project.name})")

        storage_key = get_storage().save(build_storage_key(project.id, file.name), data)
        source = Source(
            project_id=project.id,
            user_id=user.id,
            filename=file.name,
            kind=SourceKind.PDF if file.suffix.lower() == ".pdf" else SourceKind.TEXT,
            status=SourceStatus.UPLOADED,
            storage_key=storage_key,
            mime_type="application/pdf" if file.suffix.lower() == ".pdf" else "text/plain",
            size_bytes=len(data),
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        print(f"[setup] source: {source.id} ({source.filename})")

        def ingest_stage():
            return execute_ingest_stage(source.id)

        result_ingest, _ = _timed("ingest (text extraction)", ingest_stage)
        print(f"    -> extracted {len(result_ingest)} chars")

        def chunk_stage():
            return execute_chunk_stage(source.id, project.id, user.id, result_ingest)

        chunk_ids, _ = _timed("chunk", chunk_stage)
        print(f"    -> {len(chunk_ids)} chunks")

        def embed_stage():
            return execute_embed_stage(source.id, project.id, user.id, chunk_ids)

        _, _ = _timed("embed (stub + redis)", embed_stage)

        def extract_reqs():
            return execute_extract_requirements_stage(source.id, project.id, user.id)

        req_count, _ = _timed("extract requirements (Gemini)", extract_reqs)
        print(f"    -> {req_count} requirements")

        def extract_tasks():
            return execute_extract_tasks_stage(source.id, project.id, user.id)

        task_count, _ = _timed("extract tasks (Gemini)", extract_tasks)
        print(f"    -> {task_count} tasks")

        def promote():
            return promote_suggestions_to_accepted(db, user.id, project.id)

        promoted, _ = _timed("promote suggestions -> accepted", promote)
        print(f"    -> {promoted}")

        def audit():
            return run_audit(db, user.id, project.id)

        run_id, _ = _timed("audit (Gemini + risk summary)", audit)
        print(f"    -> audit run {run_id}")

        requirements = db.execute(
            select(Requirement).where(Requirement.project_id == project.id)
        ).scalars().all()
        tasks = db.execute(
            select(Task).where(Task.project_id == project.id)
        ).scalars().all()
        findings = db.execute(
            select(AuditFinding).where(AuditFinding.run_id == run_id)
        ).scalars().all()
        links = db.execute(
            select(CoverageLink).where(CoverageLink.project_id == project.id)
        ).scalars().all()

        print("\n===== RESULTS =====")
        print(f"requirements ({len(requirements)}):")
        for r in requirements:
            print(f"  - [{r.state.value}] {r.title}")
        print(f"tasks ({len(tasks)}):")
        for t in tasks:
            print(f"  - [{t.state.value}] {t.title}")
        print(f"coverage links ({len(links)}):")
        for l in links:
            print(f"  - {l.requirement_id[:8]} -> {l.task_id[:8]} [{l.status.value}]")
        print(f"audit findings ({len(findings)}):")
        for f in findings:
            print(f"  - [{f.severity.value}] {f.kind.value}: {f.message}")

        print(f"\nproject id: {project.id}")
        print(f"target: {TARGET_SECONDS:.0f}s — see per-stage times above")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
