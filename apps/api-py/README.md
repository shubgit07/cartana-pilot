# Cartana API (Python)

FastAPI backend that replaces `apps/api` (Node/Express) with the exact same API
contract, so `apps/web` and `packages/shared` require no changes. See the
root `MIGRATION_STATUS.md` for the full architecture/schema/endpoint reference
this backend must replicate.

## Status

See `PROGRESS.md` in this directory for the current migration step.

## Stack

- FastAPI
- SQLAlchemy 2.0 + Alembic
- Postgres + pgvector (`psycopg` v3 driver, `pgvector` python package)
- Redis + Celery for background jobs
- Pydantic v2 / pydantic-settings for config and schemas

## Setup

```bash
cd apps/api-py
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # or point DATABASE_URL/REDIS_URL at the existing docker-compose infra
```

This app reuses the same Postgres + Redis containers defined in the root
`docker-compose.yml` (`npm run infra:up` from the repo root) — no new infra
is introduced.

## Run

```bash
# API server
uvicorn app.main:app --reload --port 4000

# Celery worker (once task modules exist)
celery -A app.workers.celery_app.celery_app worker --loglevel=info

# Migrations (once models exist)
alembic upgrade head
```

## Tests

```bash
pytest
```

## Layout

```
app/
  main.py            FastAPI app entrypoint
  config.py          pydantic-settings Settings (env vars)
  db/                SQLAlchemy Base + session factory
  api/                 router aggregator, routes, dev-user dependency
  core/               shared errors/utilities
  providers/          AIProvider / EmbeddingProvider / StorageProvider interfaces
  workers/            Celery app + background task modules
```

Domain modules (projects, sources, chat, requirements, tasks, audit,
coverage) are added incrementally in later migration steps, each mirroring
its Node counterpart under `apps/api/src/modules/`.
