# Cartana — Agent Build Direction (3-Phase Implementation Plan)

This document is the **working instruction set for any coding agent** building Cartana.
It is written to be self-contained: an agent should be able to read this file top-to-bottom
and know *what* to build, *in what order*, *how the pieces fit*, and — critically —
*when to stop and ask the human before acting*.

The human-in-the-loop for this project is **the user (project owner)**. Treat them as the
architect and decision authority. You (the agent) are the implementer.

---

## 0. How to use this document (agent operating rules)

Read this whole file before writing any code. Then:

1. Work **phase by phase**. Do not start Phase 2 work while Phase 1 is incomplete.
2. Before any **major decision** (see §1, Decision Protocol), stop and ask the user.
3. Keep every phase **usable on its own** before moving on.
4. Prefer a **clean, maintainable** implementation over flashy complexity.
5. When something in this doc is ambiguous or conflicts with reality in the codebase,
   **surface it to the user** rather than guessing.

> This doc is a living contract. If the user approves a change to scope, stack, or schema,
> update the relevant section here **and** the product documentation so the two stay in sync.

---

## 1. Decision Protocol (human-in-the-loop) — READ FIRST

Cartana is built collaboratively. The agent must **pause and get explicit sign-off from the
user** *before* doing any of the following. Lay out the proposed change, the trade-offs, and
your recommendation, then wait for approval.

### 🔴 Requires user sign-off BEFORE proceeding
- **Schema / data-model changes** — any new table, column, index, relation, or migration.
  Show the proposed schema diff and the reason before running a migration.
- **New dependencies or stack changes** — adding any library/service, or swapping any piece
  of the agreed stack (§3). Name the dep, why it's needed, and lighter alternatives.
- **Phase transitions & scope** — starting a new phase, or adding/cutting any feature relative
  to the agreed scope. Confirm the previous phase is complete and demoable first.

### 🟡 Proceed, but report clearly
- AI prompt / extraction / coverage-judgment logic changes — you may iterate on these without
  a blocking sign-off, but **explain what you changed and why** in your summary, because these
  changes alter core product behavior.
- Non-trivial refactors that touch multiple modules.

### 🟢 Just do it
- Implementing already-agreed scope within the current phase.
- Bug fixes, formatting, tests, docstrings, small internal cleanups.

### How to ask
When a 🔴 item comes up, present it like:
> **Decision needed — [category].** I propose X because Y. Alternatives: A (…), B (…).
> My recommendation: X. This affects [schema/deps/scope]. OK to proceed?

Do not batch a 🔴 decision inside a large code change and hope it slides. Ask first.

---

## 2. Product goal (short)

Cartana is an **AI-powered project specification copilot**. Users upload project documents
(PRDs, assignment briefs, requirement docs, meeting notes), and Cartana:
- understands those documents,
- answers grounded questions over them,
- extracts structured **requirements** and **tasks**,
- and audits which requirements are **not yet covered** by tasks.

The core problem is **requirement-to-execution drift**: making sure what a brief/spec asks for
is actually reflected in the planned work. This is **not** a generic chatbot and **not** a full
project-management platform. See `cartana_documentation.md` for the full product narrative.

---

## 3. Technical stack

Build as a **TypeScript-first monorepo** with a clean, production-style structure.

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui |
| Backend | Express + TypeScript |
| Database | PostgreSQL + **pgvector** |
| ORM | Prisma |
| Queue / background jobs | Redis + BullMQ |
| Storage | Local filesystem in dev, abstracted so cloud object storage can be swapped in later |
| Embeddings | **DECIDED** — Cloudflare Workers AI `@cf/baai/bge-base-en-v1.5` → **`vector(768)`** |
| LLM generation | **Provider-agnostic `AIProvider` — start on a swappable default; final provider is an agent-discuss note (see below)** |

### Hosting / infra (recommended split)
- **Postgres + pgvector** and **Redis** self-hosted on a **DigitalOcean droplet** (self-hosting Redis
  avoids known BullMQ issues with serverless Redis offerings). One small box is enough to start.
- **Embeddings** via **Cloudflare Workers AI** (cheap, good enough, fixes the dimension).
- Keep pgvector as the single vector store (co-located with the relational data) — do **not** move
  vectors to a separate managed vector DB; that would break same-DB traceability.

### AI provider details

**Embeddings — DECIDED (locks the schema dimension):**
- Model: **Cloudflare Workers AI `@cf/baai/bge-base-en-v1.5`**, dimension **768**.
- pgvector column is **`vector(768)`**. Keep the number in a single config constant
  (`EMBEDDING_DIM = 768`) referenced everywhere.
- **This is still a 🔴 schema item** — present the embedding-column migration to the user before
  running it. Changing the embedding model later = a **re-embed migration**, not a free swap.

**LLM generation — swappable default now, final choice is an agent-discuss note:**
> Build the `AIProvider` interface and wire a **swappable default** (e.g. Cloudflare Workers AI
> generation, or Claude API — whichever is fastest to get running) so **coding is not blocked**.
> The user has **not** confirmed what LLM they'll use long-term. Notably, their **Azure / GPT-4o
> access is unconfirmed** — a GitHub Copilot subscription does *not* grant Azure OpenAI API access.
>
> **Agent action:** proceed with the swappable default and build all other parts. When extraction/
> audit quality becomes the focus (Phase 2/3), **raise the generation-provider choice with the user**
> (options: Azure OpenAI GPT-4o-mini if their Azure turns out real, Claude API, or Cloudflare Llama).
> Because generation sits behind the interface, this upgrade is **low-lock-in** and costs almost
> nothing to switch — that's why it's safe to defer.

---

## 4. Architectural principles

- **Modular code**, never one giant backend file. Express gives no structure by default, so
  impose it: one folder per domain module (`projects/`, `sources/`, `chat/`, `requirements/`,
  `tasks/`, `audit/`), each with its own `router.ts` (routes/controllers), `service.ts` (business
  logic), and job processor where relevant. Never put DB queries or AI calls directly in route
  handlers — route handlers stay thin and call into services.
- Separate: routes, services, DB access (Prisma), and background jobs (BullMQ processors).
- Keep the **AI layer abstracted behind services** (`AIProvider`, `EmbeddingProvider`). No raw
  provider SDK calls scattered across the codebase.
- Keep **prompt logic separated from business logic** (a `prompts/` area or dedicated modules).
- **Maintain traceability**: every extracted requirement and task links back to its source
  document and, where possible, the specific chunk(s) it came from.
- Keep the app **buildable and demoable in phases**.
- **Do not over-engineer multi-agent workflows.** Only the audit / coverage-analysis flow (Phase 3)
  should feel agentic. Everything else is plain services + jobs.

---

## 5. Core data model — DEFINE UP FRONT (Phase 1)

Define the **full schema up front** in Phase 1, even for tables that stay empty until later
phases. This avoids costly migration rewrites and keeps traceability correct from day one.
(Creating these tables is a 🔴 schema change — present the Prisma schema to the user for sign-off
before the first migration.)

Core entities (names indicative; confirm exact fields with the user):

- **User** — present from Phase 1 even though auth is single-user (see §6). Everything is
  `userId`-scoped so multi-user can be added later without a rewrite.
- **Project** — a workspace. Belongs to a User.
- **Source** — an uploaded document/note. Belongs to a Project. Stores storage metadata,
  file type, status (uploaded → processing → processed → failed).
- **Chunk** — a text chunk of a Source. Holds the text, position/offsets, and the **embedding**
  (`vector(EMBEDDING_DIM)`). Used for retrieval and traceability.
- **Requirement** — a structured requirement extracted from sources. Links back to the
  Source/Chunk(s) it came from. Has an origin flag (`ai` vs `user`) and edit/review state.
- **Task** — an actionable work item. May be `ai`-suggested or `user`-created (see §7). Has
  review state (suggested / accepted / rejected / edited) and links to source where possible.
- **CoverageLink** — the relationship between a Requirement and a Task. Carries coverage status
  (covered / partial / unclear) and an origin flag (`ai-suggested` vs `user-confirmed`).
- **AuditRun** — one execution of the audit engine over a project at a point in time.
- **AuditFinding** — a single finding from an AuditRun (e.g. uncovered requirement, vague
  requirement, deadline risk), linked to the relevant requirement/task.

Every AI-generated row carries an **origin** and **review state** so the user can trust, edit,
or override it. The audit is only trustworthy if the underlying data can be corrected by the user.

---

## 6. Auth & tenancy — DECIDED: single-user local MVP

- **Phase 1 has no login.** Use a single implicit/dev user.
- **But the schema is multi-user-ready:** every project-scoped table carries a `userId`.
- Real authentication is deferred to a **later phase** and must not require reworking the data
  model — only adding a session/identity layer on top. Adding auth later is a 🔴 scope change:
  confirm with the user when the time comes.

---

## 7. Task management — DECIDED: AI-suggested + full manual edit

Tasks are **not** read-only AI output. The user can:
- **create** tasks manually,
- **edit** task title/summary,
- **accept / reject** AI-suggested tasks,
- **relink** a task to a different requirement (manage CoverageLinks).

Consequences for the build:
- `Task.origin` = `ai | user`; `Task.state` = `suggested | accepted | rejected | edited`.
- `CoverageLink.origin` = `ai-suggested | user-confirmed`. **User-confirmed links win** and must
  survive re-extraction — do not blow away user edits when reprocessing (see §8).
- The coverage audit reasons over the **effective** task list (accepted + user-created), not raw
  AI suggestions.

---

## 8. Cross-cutting concerns

### 8.1 Traceability
Requirements and tasks store references to the Source (and Chunk(s)) they derive from. The UI
should be able to show "where did this come from" for any extracted item.

### 8.2 Async processing
Document text extraction, chunking, embedding, requirement/task extraction, and audit generation
run as **BullMQ background jobs**. The API kicks off jobs and reports status; it does not block on
long AI work. Surface job status (processing / done / failed) to the UI.

### 8.3 Re-processing & idempotency (do not skip)
Define clear behavior for when a Source is re-uploaded/edited, or a new Source changes scope:
- Re-extraction must be **idempotent** — re-running should not create duplicate requirements/tasks.
- **User edits and user-confirmed coverage links are preserved** across re-extraction.
- AI-suggested-but-superseded items should be updated or marked stale, not silently duplicated.
- Basic re-extract behavior is required in **Phase 2**. Full "requirement change tracking / scope
  diffing" is a future expansion, not MVP.

### 8.4 Provider replaceability
LLM generation, embeddings, and storage sit behind interfaces so they can be swapped. Remember:
generation swaps are free; **embedding-model swaps are a re-embed migration** (§3).

### 8.5 Dev environment (part of Phase 1 "production-style" setup)
Include, in Phase 1:
- a **docker-compose** for Postgres+pgvector and Redis,
- Prisma **migrations** (not `db push` for the committed schema),
- **seed data** for quick local testing,
- a documented **run/setup** flow (env vars, how to start web + api + worker),
- a basic **testing** approach (at least unit tests for services and one end-to-end happy path).

Adding docker-compose/tooling deps is a 🔴 new-dependency step — but propose it as part of the
Phase 1 setup plan and get sign-off once, up front.

---

## 9. Phase 1 — Core project + document chat foundation

### Goal
Build the shell and the minimum usable workflow: create a project → upload documents → process
into chunks → store embeddings → chat/Q&A over the material. At the end, Cartana is already a
usable **project-specific document assistant**.

### Frontend
- basic app shell (single-user, no login screen; dev user implicit)
- project list page
- create-project flow
- project detail page
- upload-documents section + source/document list for a project
- chat interface for grounded Q&A over the project's documents
- job/processing status indicators

### Backend
- project CRUD
- source/document upload registration + storage metadata
- source processing pipeline kickoff (enqueue jobs)
- retrieval pipeline (fetch relevant chunks via pgvector)
- chat endpoint for project-level grounded Q&A (retrieval-augmented, cites sources)

### Data / processing
- source storage metadata
- text extraction for **PDF + plain text** (start here; images/screenshots are future)
- chunking strategy
- embedding generation (via `EmbeddingProvider` — **respect the OPEN DECISION in §3**)
- vector storage in pgvector
- retrieval logic for answering project questions

### Phase 1 output (demoable flow)
1. User creates a project
2. User uploads a brief / PRD / notes
3. System processes the document (async, with status)
4. User opens project chat
5. User asks e.g. "What are the main requirements?", "What deadlines are mentioned?",
   "What does the project expect for the dashboard module?" — and gets grounded answers.

### Phase 1 constraints
- Do **not** build task extraction yet (a stub is fine if needed).
- Do **not** build a large dashboard.
- Do **not** build collaboration features.
- Focus on clean ingestion + retrieval + grounded chat.

> ✅ Before starting Phase 1 coding: present the **full Prisma schema (§5)** and the **Phase 1
> dependency/setup list (§8.5)** to the user for sign-off (🔴 schema + deps).
> Also clear the **AI provider OPEN DECISION (§3)** before running the embedding migration.

---

## 10. Phase 2 — Requirement & task extraction layer

### Goal
Turn "chat with docs" into a real copilot by extracting structured project information: what the
project requires, and what tasks can be derived from those requirements.

### Backend
- requirement extraction from sources (with source/chunk traceability)
- task extraction / suggestion from requirements + source text
- persistence for requirements and tasks (schema already exists from §5)
- source-to-requirement and source-to-task traceability
- **re-processing behavior per §8.3** (idempotent, preserves user edits)
- endpoints for the manual task management from §7 (create/edit/accept/reject/relink)

### Frontend
- **Requirements view** — list extracted requirements; allow review/edit; show source link
- **Tasks view** — list AI-suggested + user-created tasks; show title, summary, linked
  requirement/source; support accept / reject / edit / create / relink

### Processing behavior
When a source is uploaded or reprocessed: extract candidate requirements, extract candidate
tasks, save against the project, link to source documents/chunks where possible — **without
clobbering user edits**.

### Phase 2 output
User can upload a brief, chat about it, open **Requirements** to see extracted requirements, and
open **Tasks** to see suggested + manually managed work items derived from the docs.

### Phase 2 constraints
- Keep extraction practical and reviewable.
- Do not build a Jira/Trello replacement.
- Keep UX focused on "understanding project scope," not full task management.

> ✅ Phase 2 starts only after Phase 1 is complete and demoable (🔴 phase transition).

---

## 11. Phase 3 — Coverage audit + risk detection

### Goal
Build the feature that makes Cartana different from a normal RAG app: **requirement coverage
auditing**. Check whether extracted/managed tasks actually cover the requirements, and surface
missing or risky areas.

### Coverage-mapping mechanism (specify it — don't hand-wave "agentic")
The mapping from requirements → tasks works in two stages:
1. **Candidate retrieval:** for each requirement, use embedding similarity to retrieve the most
   relevant tasks (and/or source chunks) as candidate matches.
2. **LLM judgment pass:** an LLM classifies each requirement's coverage as
   **covered / partial / unclear / missing**, with a short rationale, considering the candidate
   tasks. Results are written as **CoverageLink** rows + **AuditFinding** rows.

User-confirmed coverage links (§7) are treated as ground truth and not overridden by the AI pass.

### Backend — audit/analysis module
- compare requirements against the effective task list
- identify requirements with: no coverage / partial coverage / unclear coverage
- generate **AuditFinding**s and a short **project risk summary**
- optionally flag vague requirements or requirements with no clear implementation path
- persist each run as an **AuditRun** (so history is possible later)

### Frontend — Coverage / Audit view
- requirement coverage status: covered / partial / missing buckets
- audit findings list
- project risk summary

### Agentic behavior (contained)
This is the **only** place the system should feel agentic. The audit flow can behave like an
analysis agent that: reviews requirements → reviews the effective tasks → reasons about missing
coverage → produces structured findings + a human-readable summary. **Keep this contained to the
audit feature.** Do not turn the whole codebase into a generic agent system.

### Phase 3 output
User can upload docs, chat, see requirements, see tasks, and open **Audit** to understand which
requirements are covered, which are missing, and what risks exist before submission/delivery.

> ✅ Phase 3 starts only after Phase 2 is complete and demoable (🔴 phase transition).

---

## 12. Build priorities across all phases

1. **Clean project structure** — modular folders, no mixed concerns, easy to navigate.
2. **Traceability** — requirements/tasks link back to source material as much as possible.
3. **Async processing** — ingestion, embeddings, extraction, audit run as background jobs.
4. **Replaceability** — LLM/embeddings/storage behind interfaces (mind the embedding-dimension caveat).
5. **Keep the product focused** — do not expand into team chat, generic assistant, enterprise PM,
   website scraping, or complex multi-agent orchestration.

---

## 13. Coding standards

- TypeScript everywhere.
- Clear module boundaries; small services with single responsibility.
- Prompt logic separated from business logic.
- Validate input/output contracts (DTOs / zod / class-validator).
- Write code that extends later without major rewrites.
- Never hardcode AI provider logic across many files — go through the abstraction.
- Keep data models explicit and stable (schema changes are 🔴).
- Comment where architecture/flow is non-obvious.
- Each phase must be usable on its own before moving to the next.

---

## 14. What NOT to do

- Build all features at once, or make v1 a giant platform.
- Add dashboards before core workflows work.
- Overcomplicate the AI layer or spread provider SDK calls everywhere.
- Tightly couple UI and extraction logic.
- Make assumptions that break future provider/database changes.
- Run a schema migration, add a dependency, or change scope **without user sign-off** (§1).
- Prematurely optimize for enterprise scale.

---

## 15. Open decisions log

Keep this current. When a decision is made, record it here and update the relevant section.

| # | Decision | Status | Notes |
|---|---|---|---|
| 1 | LLM generation provider | **DEFERRED — agent-discuss note** | Behind `AIProvider`. Start on a swappable default (Cloudflare/Claude) so coding isn't blocked; raise final choice with user in Phase 2/3. Azure/GPT-4o access unconfirmed. Low lock-in. |
| 2 | Embedding model + dimension | **DECIDED** | Cloudflare Workers AI `bge-base-en-v1.5` → `vector(768)`. `EMBEDDING_DIM=768`. Still a 🔴 migration to run; changing later = re-embed. |
| 7 | Hosting / infra | **DECIDED** | Postgres+pgvector + Redis self-hosted on DigitalOcean droplet; embeddings via Cloudflare Workers AI; single pgvector store. |
| 3 | Auth / tenancy | **DECIDED** | Single-user local MVP; `userId` columns present; real auth later. |
| 4 | Task management depth | **DECIDED** | AI-suggested + full manual create/edit/accept/reject/relink. |
| 5 | Sign-off checkpoints | **DECIDED** | Schema changes, new deps/stack, phase transitions & scope (§1). |
| 6 | Product name | **DECIDED** | Cartana. |

---

## 16. Final instruction to the coding agent

Implement Cartana as a **focused AI product for project-spec understanding and requirement
coverage auditing**, in three phases:

- **Phase 1:** project + document ingestion + grounded project chat
- **Phase 2:** requirement extraction + task extraction (with manual task management)
- **Phase 3:** requirement coverage audit + risk summary

At every phase, prefer a clean, maintainable implementation over flashy complexity — and **stop to
ask the user before any schema change, new dependency, or phase/scope change (§1).**
