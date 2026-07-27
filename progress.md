# Cartana — Build Progress & Items Needing Your Attention

This file tracks what has been built, what's pending, and — most importantly —
**what requires your sign-off or action before it can move forward**.

See the agent build plan in `cartana_agent_3_phase_plan.md` for the full phasing.

---

## Status overview

| Phase | Status |
|---|---|
| **Phase 1** — Project shell + doc ingestion + grounded chat | ✅ Code complete (pending DB migration / env wiring on your end) |
| **Phase 2A** — Requirement extraction + review UI | ✅ Code complete |
| **Phase 2B** — Task extraction + manual task management UI | ✅ Code complete |
| Phase 3 — Coverage audit + risk summary | ⏸ Not started |

---

## 🔴 Items that need YOUR attention before the system fully runs

These are things I deliberately did **not** hardcode, because they require your
environment / credentials / final choice.

### 1. Postgres + pgvector connection
- **Where:** `.env` → `DATABASE_URL`
- **Default I provided:** `postgresql://cartana:cartana@localhost:5432/cartana?schema=public`
- **Action:** Copy `.env.example` to `.env` in the repo root. If you run the
  `docker-compose.yml`, the default works out of the box.
- **Run it:** `npm run infra:up`
- **Apply schema:** `npm run db:migrate` (applies both migrations in order)
- **Seed sample data:** `npm run db:seed`

### 2. Cloudflare Workers AI credentials (for real embeddings)
- **Where:** `.env` → `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`
- **Status:** DECIDED in plan — `@cf/baai/bge-base-en-v1.5` → `vector(768)`.
- **Behavior if left empty:** system runs in **stub mode** (deterministic
  pseudo-embeddings so the pipeline never crashes). Retrieval works but
  quality will be poor until real embeddings are wired in.
- **Action:** Create a Cloudflare account → get an API token with Workers AI
  permission → paste into `.env`.

### 3. LLM provider (for grounded chat answers + extraction)
- **Where:** `.env` → `LLM_PROVIDER`, plus matching key (e.g. `OPENAI_API_KEY` or
  `ANTHROPIC_API_KEY` or `CLOUDFLARE_LLM_MODEL`).
- **Status:** OPEN DECISION in the plan — I built a swappable `AIProvider` interface
  so this is **low lock-in** to change later.
- **Behavior if left as `stub`:** chat returns a retrieval-only answer (the
  top-matching passages are stitched together as the response, with citations).
  Requirement + task extraction uses a heuristic regex-based stub. This lets
  you exercise the full flow without paying for an LLM yet.
- **Action (when ready):** pick a provider and add the key. Options surfaced
  in §3 of the plan: Azure OpenAI GPT-4o-mini, Claude API, or Cloudflare Llama.

### 4. 🔴 First-time Prisma migration (schema sign-off)
- The Prisma schema defines **all** core tables (User, Project, Source, Chunk,
  Requirement, Task, CoverageLink, AuditRun, AuditFinding) up front, per §5.
- **Action:** Run `npm run db:migrate` once. The repo includes two migrations:
  - `20260101000000_init/` — all tables + `vector(768)` column + indexes.
  - `20260101000100_phase2_dedupe_key/` — adds `dedupeKey` to `Requirement` and `Task`
    (needed for idempotent re-extraction per plan §8.3).
  If Prisma rejects either migration (e.g. hash mismatch because of formatting),
  delete the folder(s) and let Prisma regenerate from the schema — the result
  will be functionally equivalent.
- **Review** the generated SQL before applying in any non-local environment.
  Any future schema change is a 🔴 sign-off item per the plan.

---

## 🟡 Things to know but not block on

- **Auth is intentionally absent.** There is a single implicit `dev-user`. The
  schema carries `userId` everywhere so real auth can be bolted on later
  without a data-model rewrite (🔴 scope change when we do it).
- **Re-extraction idempotency** is live for both requirements and tasks. The
  extractor computes `dedupeKey = sha256(sourceId + normalized(title))`. On
  re-run: matching rows are refreshed if they're still AI-suggested; rows the
  user has accepted/edited/rejected are never overwritten; AI rows whose
  `dedupeKey` is no longer seen are marked `state=rejected` (not deleted).
  User-created rows (origin=user) are always preserved.
- **Storage** is local filesystem in dev (`STORAGE_LOCAL_ROOT=./storage`).
  The `StorageProvider` is abstracted so cloud object storage can replace it
  later without touching call sites.
- **pgvector extension** is enabled via the first migration; the docker image
  `pgvector/pgvector:pg16` already has the extension installed — the migration
  runs `CREATE EXTENSION IF NOT EXISTS vector;` for you.
- **Phase 2B is now complete.** The Tasks tab UI (TasksPanel) is built and
  integrated, with full manual management: create, edit, accept, reject,
  delete, and relink tasks to requirements. The backend was already wired
  last session. See "Phase 2B — what was built" below.

---

## Phase 1 — what was built

### Repo / infra
- Monorepo layout: `apps/api` (Express + TS), `apps/web` (Next.js + TS), `packages/shared` (zod + types + constants).
- `docker-compose.yml` for Postgres+pgvector and Redis.
- Root `package.json` with workspace scripts: `dev:api`, `dev:web`, `build`,
  `db:migrate`, `db:seed`, `infra:up`.
- `.env.example` documenting every var with TODOs in the right places.

### Shared package (`packages/shared`)
- `EMBEDDING_DIM = 768` constant (single source of truth).
- `QUEUE_NAMES` for BullMQ.
- Zod input schemas (create/update project, create source from text, chat ask).
- API contract types (project/source/chat summaries, citations, job status).

### API (`apps/api`) — modular structure
- `src/index.ts` — bootstrap.
- `src/server.ts` — Express app factory (CORS, JSON, multipart, error handler).
- `src/config.ts` — env loading with zod validation.
- `src/lib/logger.ts` — pino logger.
- `src/lib/errors.ts` — typed app errors.
- `src/db/prisma.ts` — Prisma client singleton.
- `src/queue/connection.ts` — Redis connection.
- `src/queue/queues.ts` — BullMQ queue definitions.
- `src/storage/StorageProvider.ts` — interface + local-fs implementation.
- `src/ai/EmbeddingProvider.ts` — interface + Cloudflare + stub impls.
- `src/ai/AIProvider.ts` — interface + stub impl (retrieval-only answer).
- `src/prompts/chat.ts` — chat prompt separated from business logic.
- `src/modules/projects/` — router + service + dev-user guard.
- `src/modules/sources/` — router (multipart + text-paste upload) + service + text extraction (PDF + plain).
- `src/modules/chat/` — router + retrieval service + answer service.
- `src/jobs/ingest.ts`, `chunk.ts`, `embed.ts` — job processors.
- `src/workers/index.ts` — BullMQ worker entry point.
- `prisma/schema.prisma` — full schema (User, Project, Source, Chunk, Requirement, Task, CoverageLink, AuditRun, AuditFinding).
- `prisma/migrations/...` — initial migration including `CREATE EXTENSION vector` and the `vector(768)` column.
- `prisma/seed.ts` — dev user + one demo project.

### Web (`apps/web`) — normal, future-proof Next.js app
- App Router with a clean, minimal UI (no marketing-style chrome).
- Tailwind + a tiny set of shadcn/ui-style primitives (Button, Card, Input, Textarea, Badge, Skeleton, Label, Toast) — **hand-rolled in-repo** so there is no extra CLI install step and the codebase stays self-contained.
- Pages: `/` (project list), `/projects/new`, `/projects/[id]` (overview + sources + requirements + chat).
- API client + hooks (`useProjects`, `useProject`, `useSources`, `useChat`, `useRequirements`, `useTasks`).
- Polling for source processing status (so the user sees chunks being embedded in real time).
- Citations panel inside the chat (which document + chunk the answer referenced).

---

## Phase 2A — what was built (now complete)

### 🔴 Schema addition
- Added **`dedupeKey String?`** to `Requirement` and `Task` for idempotent
  re-extraction per plan §8.3. New migration
  `apps/api/prisma/migrations/20260101000100_phase2_dedupe_key/` applies it.
  You will run both migrations when you run `npm run db:migrate`.

### Backend
- `apps/api/src/ai/extractors/requirementExtractor.ts` — regex-based stub
  extractor that finds sentences containing requirement keywords (`must`,
  `should`, `shall`, `required to`, …). When a real LLM is wired in, the
  same shape is produced via a prompt.
- `apps/api/src/ai/extractors/taskExtractor.ts` — same shape for tasks
  (action-verb based), with best-effort linkage to requirements by token
  overlap. Used by Phase 2B too.
- `apps/api/src/ai/AIProvider.ts` — added `extractRequirements()` and
  `extractTasks()` to the interface. Both stub and Cloudflare providers
  implement them.
- `apps/api/src/jobs/extractRequirements.ts` — new BullMQ job. Idempotent
  upsert + stale-out for superseded AI-suggested requirements.
- `apps/api/src/jobs/embed.ts` — after embedding completes, enqueues
  `extractRequirements`. From there, extractRequirements enqueues
  `extractTasks` (Phase 2B backend).
- `apps/api/src/lib/dedupe.ts` — `sha256(sourceId + normalized(title))` helper.
- `apps/api/src/modules/requirements/` — service + router. Endpoints:
  - `GET /projects/:projectId/requirements` — list (with source links).
  - `GET /projects/:projectId/requirements/:id` — detail (with chunk snippets).
  - `PATCH /projects/:projectId/requirements/:id` — edit title/description or
    accept/reject. Touching a row flips origin from `ai` → `user`.
  - `DELETE /projects/:projectId/requirements/:id` — remove.
- `apps/api/src/queue/queues.ts` — added two queues
  (`extractRequirements`, `extractTasks`) + their `JobData` types.
- `apps/api/src/workers/index.ts` — registers workers for both new queues.
- `apps/api/src/server.ts` — mounts `/projects/:projectId/requirements`.

### Shared package
- `RequirementSummary`, `RequirementDetail`, `TaskSummary`, `TaskDetail` types.
- Zod schemas: `UpdateRequirementSchema`, `CreateTaskSchema`, `UpdateTaskSchema`.

### Web
- `apps/web/src/lib/api.ts` — added `listRequirements`, `updateRequirement`,
  `deleteRequirement` (plus the parallel `tasks` methods for Phase 2B).
- `apps/web/src/hooks/useApi.ts` — added `useRequirements` and `useTasks` hooks.
- `apps/web/src/components/project/RequirementsPanel.tsx` — list + inline
  edit + accept/reject + delete, with state and origin badges, source-file
  provenance, and inline editing of title/description.
- `apps/web/src/app/projects/[id]/page.tsx` — added the **Requirements** tab
  between Sources and Chat.

### Idempotency contract (this is important, plan §8.3)
- Re-uploading the same source → re-runs extract → upserts by `dedupeKey`.
- User `accepted` / `rejected` / `edited` rows are **never** overwritten by
  re-extraction.
- AI-suggested rows whose `dedupeKey` is no longer in the freshly-extracted
  set are marked `state=rejected` (so they hide from the active list but
  stay in the DB for history/audit in Phase 3).

---

## What's intentionally NOT in Phase 2A
- **Coverage audit** (Phase 3).
- **Audit runs + findings** schema exists but no engine yet.
- **Multi-user auth** (deferred — schema is multi-user-ready).
- **Image / screenshot ingestion** (future expansion per plan §17.2).

---

## Phase 2B — what was built (now complete)

Backend was wired in the prior session (task extractor stub, `extractTasks`
job, `tasks` service + router, `useTasks` + `useRequirements` hooks, API client
methods). This session added the UI.

### Web
- `apps/web/src/components/project/TasksPanel.tsx` — full task management UI:
  - **List** tasks with state/origin badges, linked-requirement chip, source-file
    provenance. Rejected rows are dimmed (consistent with RequirementsPanel).
  - **Create** — top "+ New task" button reveals an inline form (title,
    description, optional requirement link). No modal dependency.
  - **Edit** — inline title/description + a requirement `<select>` for relinking.
  - **Accept / Reject** — hidden once decided (same UX as RequirementsPanel).
  - **Delete** — with confirm.
  - Reuses `useTasks` and `useRequirements` (the latter populates the relink
    dropdown, filtered to non-rejected requirements).
- `apps/web/src/app/projects/[id]/page.tsx` — added the **Tasks** tab between
  Requirements and Chat.

### Idempotency contract (same as requirements, plan §8.3)
- Re-extraction upserts tasks by `dedupeKey`; user-accepted/edited/rejected
  rows are never overwritten; superseded AI-suggested tasks are marked
  `state=rejected`.

---

## What's intentionally NOT in Phase 2 (both A + B)
- **Coverage audit** (Phase 3).
- **Audit runs + findings** schema exists but no engine yet.
- **Multi-user auth** (deferred — schema is multi-user-ready).
- **Image / screenshot ingestion** (future expansion per plan §17.2).

---

## How to run locally (when you're ready)

```bash
# 1. Copy env
cp .env.example .env

# 2. Start infra (Postgres+pgvector + Redis)
npm run infra:up

# 3. Install workspaces
npm install

# 4. Apply DB schema + seed
npm run db:migrate
npm run db:seed

# 5. Start the app
# Option A — single process (worker runs in-process with the API; default):
npm run dev:api
npm run dev:web
# (set CARTANA_WORKER_MODE=false in .env if you want API-only)

# Option B — separate worker process:
npm run dev:worker   # terminal 1 — BullMQ worker
npm run dev:api      # terminal 2 — Express API on :4000
npm run dev:web      # terminal 3 — Next.js on :3000
```

Open `http://localhost:3000`. Create a project → upload a brief → wait for
chunks to embed → ask a question in the chat.

---

## What's intentionally NOT in Phase 1
(per §9 of the plan — do not pull these forward)

- Requirement extraction (Phase 2)
- Task extraction / manual task management (Phase 2)
- Coverage audit + risk summary (Phase 3)
- Multi-user auth (later phase, schema is already multi-user-ready)
- Image / screenshot ingestion (future expansion)
- Team collaboration features

These have placeholders / data models defined but no behavior.