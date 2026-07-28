# Python migration progress

Tracks migration steps for `apps/api-py` against `MIGRATION_STATUS.md`.

| Step | Description | Status |
|---|---|---|
| 1 | Project scaffolding + config (FastAPI app, settings, db session, Alembic init, Celery app, provider interfaces, health check) | Done |
| 2 | Database schema (SQLAlchemy models for the 10 tables, mirroring `schema.prisma`) + first Alembic migration | Not started |
| 3 | Projects module (CRUD) | Not started |
| 4 | Sources module (upload, ingest pipeline kickoff) | Not started |
| 5 | Background pipeline: ingest -> chunk -> embed | Not started |
| 6 | Chat (RAG) endpoint | Not started |
| 7 | Requirements extraction + endpoints | Not started |
| 8 | Tasks extraction + manual task management endpoints | Not started |
| 9 | Coverage audit engine + endpoints | Not started |
| 10 | Provider implementations (stub, Cloudflare, Fireworks) | Not started |
| 11 | Contract verification against `apps/web` + cutover plan | Not started |

Note: per `cartana_agent_3_phase_plan.md`, schema changes (Step 2) require
explicit sign-off before any migration is run.
