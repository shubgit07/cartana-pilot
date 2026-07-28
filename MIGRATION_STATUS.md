# Cartana — Current Project Status

**Date:** July 2026
**Branch:** `dev` (migration branch)

## What Cartana Is

An AI-powered project specification copilot. Users upload project documents, chat over them (RAG), AI extracts requirements + tasks, and runs a coverage audit to find gaps.

## Architecture

```
cartana-new/
  apps/
    api/          Node.js + Express + TypeScript backend + BullMQ workers
    web/          Next.js 16 + React 19 + TypeScript frontend
  packages/
    shared/       Shared types, Zod schemas, constants
  docker-compose.yml   (Postgres 16 + pgvector + Redis 7)
```

## Tech Stack (Current — Node.js Backend)

| Layer | Tech |
|---|---|
| Runtime | Node.js ≥ 20.9, TypeScript 5.6 |
| HTTP | Express 5.2 |
| ORM | Prisma 6.5 |
| Database | PostgreSQL 16 + pgvector extension |
| Queue | BullMQ 5.12 + Redis 7 |
| File Upload | multer (in-memory, 25MB limit) |
| PDF Parsing | pdf-parse |
| Validation | Zod 3.23 |
| AI Providers | Stub (heuristic), Cloudflare Workers AI, Fireworks AI |
| Embeddings | Cloudflare BGE-base-en-v1.5 (768-dim) or stub |
| Testing | Vitest |

## Frontend Status: COMPLETE

All 6 feature domains fully implemented with real UI, no placeholders:

- **Project CRUD** — create, list, detail, delete
- **Document Ingestion** — file upload (PDF/text), paste notes, live status polling
- **RAG Chat** — ask questions, cited answers, suggested questions, localStorage history
- **Requirements** — list, accept/reject/edit, source traceability
- **Tasks** — list, accept/reject/edit, create manual, link to requirements
- **Coverage Audit** — run audit, risk summary, findings by severity, coverage matrix with overrides

Also complete: dark mode, accessibility, loading/error/empty states, Tailwind CSS, Radix UI primitives.

## Backend Status: COMPLETE (with stub AI quality)

All endpoints wired and functional. Background pipeline works end-to-end. Extractors use heuristic/regex (stub quality) — switching to real LLM is an env var change.

### API Modules

| Module | Path | Endpoints |
|---|---|---|
| Projects | `/projects` | GET, POST, GET /:id, PATCH /:id, DELETE /:id |
| Sources | `/projects/:pid/sources` | GET, POST (file), POST /text, GET /:sid, GET /:sid/status, DELETE /:sid |
| Chat | `/projects/:pid/chat` | POST |
| Requirements | `/projects/:pid/requirements` | GET, GET /:id, PATCH /:id, DELETE /:id |
| Tasks | `/projects/:pid/tasks` | GET, POST, GET /:id, PATCH /:id, DELETE /:id |
| Audit | `/projects/:pid/audit` | POST /run, GET /runs, GET /latest, GET /run/:jid/status |
| Coverage | `/projects/:pid/coverage` | GET, PATCH /:lid |

### Background Job Pipeline (6 BullMQ queues, chained)

```
Upload → ingest → chunk → embed → extractRequirements → extractTasks
                                                      → runAudit (manual)
```

### Database Schema (10 tables via Prisma)

User, Project, Source, Chunk (with vector(768)), Requirement, RequirementChunk, Task, TaskChunk, CoverageLink, AuditRun, AuditFinding

### Key Design Patterns

- **Thin route handlers** — validate input, call service, return DTOs
- **Idempotent extraction** — dedupeKey = sha256(sourceId + normalized title)
- **User edits are sacred** — accepted/rejected/edited rows never overwritten by re-extraction
- **User-confirmed coverage links survive re-audit** as ground truth
- **Provider interfaces** — AIProvider, EmbeddingProvider, StorageProvider (swappable)
- **Dev user middleware** — no real auth yet (deferred)

## What the Python Migration Needs to Replicate

1. FastAPI app with same route structure and DTOs
2. SQLAlchemy + Alembic for same 10-table schema (with pgvector)
3. Background job system (Celery/ARQ + Redis)
4. AI/LLM provider layer (stub, Cloudflare, Fireworks)
5. Embedding provider layer (stub, Cloudflare)
6. File upload + local storage
7. pgvector cosine similarity search for RAG chat
8. Coverage audit engine
9. All business logic from services (idempotent upsert, stale-out, dedupe)

## What Does NOT Change

- `apps/web/` — frontend stays as-is (Next.js calls same API endpoints)
- `packages/shared/` — types/schemas stay (Python backend must return same DTOs)
- `docker-compose.yml` — Postgres + Redis stays

## How to Run Current Node.js Backend

```bash
npm run infra:up          # Postgres + pgvector + Redis
npm run db:generate       # Prisma client
npm run db:migrate        # Apply migrations
npm run db:seed           # Dev user + demo project
npm run dev:api           # API + worker on port 4000
npm run dev:web           # Next.js on port 3000
```
