# Cartana API (Python)

FastAPI backend that replaced `apps/api` (Node/Express) with the exact same API
contract, so `apps/web` and `packages/shared` require no changes. See
`PROGRESS.md` in this directory for the migration status.

## Status

See `PROGRESS.md` in this directory for the current migration step.

## Stack

- FastAPI
- SQLAlchemy 2.0 + Alembic
- Postgres + pgvector (`psycopg` v3 driver, `pgvector` python package)
- Redis + ARQ for background jobs
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
# API server. --reload-include '.env' restarts the process when .env changes,
# so provider configuration edits take effect immediately (12-factor: env is
# captured at process start).
uvicorn app.main:app --reload --reload-include '.env' --port 4000

# ARQ worker (background jobs)
arq app.workers.arq_worker.WorkerSettings

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
  workers/            ARQ worker + background task modules
```

Domain modules (projects, sources, chat, requirements, tasks, audit,
coverage) are added incrementally in later migration steps, each mirroring
its Node counterpart under `apps/api/src/modules/`.
