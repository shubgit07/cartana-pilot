# AGENTS.md — Cartana Monorepo

Conventions for AI agents and humans editing this codebase.

## Project

Cartana is an AI-powered project specification copilot. Users upload project documents, chat over them, extract requirements + tasks, and audit requirement coverage.

## Monorepo layout

```
apps/api/        Express + TypeScript API + BullMQ workers
apps/web/        Next.js 16 + TypeScript frontend
packages/shared/ Shared types, zod schemas, constants
```

## Commands

```bash
# Infra
npm run infra:up          # Postgres + pgvector + Redis (docker-compose)
npm run infra:down

# Database
npm run db:generate       # Prisma client
npm run db:migrate        # Apply migrations
npm run db:seed           # Dev user + demo project

# Dev
npm run dev:api           # API + worker (terminal 1)
npm run dev:web           # Next.js (terminal 2)

# Build
npm run build:shared      # Shared package (must run first)
npm run build:api         # API
npm run build:web         # Web

# Tests
npm test                  # All workspaces
npm run test -w @cartana/api
npm run test -w @cartana/web

# Lint
npm run lint -w @cartana/web
```

## Phase status

| Phase | Status |
|---|---|
| Phase 1 — Project shell + doc ingestion + grounded chat | ✅ |
| Phase 2A — Requirement extraction + review UI | ✅ |
| Phase 2B — Task extraction + manual task management UI | ✅ |
| Phase 3 — Coverage audit + risk summary | ✅ |
| Auth | Deferred (after Phase 3, before second user) |

## Architecture rules

- **Modular code.** API: one folder per domain module (`projects/`, `sources/`, `chat/`, `requirements/`, `tasks/`, `audit/`), each with `router.ts` + `service.ts`. Web: vertical-slice `features/` folders.
- **Route handlers stay thin.** Validate input, call service, return DTOs. No DB queries or AI calls in routers.
- **AI layer behind interfaces.** `AIProvider`, `EmbeddingProvider`, `StorageProvider`. No raw SDK calls scattered across modules.
- **Prompt logic separated from business logic.** Prompts live in `src/prompts/`.
- **Traceability.** Every extracted requirement/task links back to its source/chunk.
- **Async processing.** Ingestion, embeddings, extraction, audit run as BullMQ background jobs.
- **Idempotent re-extraction.** User edits/accepted/rejected rows are never overwritten. `dedupeKey` = sha256(sourceId + normalized title).
- **User-confirmed coverage links are ground truth.** AI-suggested links can be replaced; user-confirmed links survive re-audit.

## Schema changes are 🔴

Any new table, column, index, or migration requires explicit user sign-off before running. Present the schema diff and reason first.

## LLM providers

| Provider | Env | Notes |
|---|---|---|
| `stub` | `LLM_PROVIDER=stub` | Heuristic-only. Works end-to-end but low quality. |
| `cloudflare` | `LLM_PROVIDER=cloudflare` + CF credentials | Workers AI. Already wired. |
| `fireworks` | `LLM_PROVIDER=fireworks` + `FIREWORKS_API_KEY` | OpenAI-compatible. JSON mode for structured output. **Recommended for Phase 3 audit.** |

## Web frontend conventions

See `apps/web/AGENTS.md` for the full frontend convention guide (modular split, accessibility, dark mode, forms, etc.).

## Testing

- `vitest` in both `apps/api` and `apps/web`.
- API tests: pure-function unit tests for `dedupe`, `errors`, `chunking`, extractors, `coverageStub`.
- Web tests: `format`, `cn`, `constants`, `storage`.
- Run `npm test` from root to run all workspaces.

## What NOT to do

- Run a schema migration without user sign-off.
- Add a new npm dependency without explaining why and naming lighter alternatives.
- Put DB queries or AI calls in route handlers.
- Use native `confirm()` / `alert()` / `<select>` in the web app.
- Use `transition: all` in CSS.
- Use `new Date().toLocaleDateString()` directly in the web app (use `formatDate()` from `@/lib/format`).
