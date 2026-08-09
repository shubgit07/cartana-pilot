# AGENTS.md — Cartana Monorepo

Conventions for AI agents and humans editing this codebase.


## RULES non negotiable 
1) Dont edit, commit bash command run or any destructive operation without users explicit permission.
2) Reading is allowed codebase files .
3) write production ready practices codes .


## Project


Cartana is an AI-powered project specification copilot. Users upload project documents, chat over them, extract requirements + tasks, and audit requirement coverage.

## Monorepo layout

```
apps/api-py/     python backend
apps/web/        Next.js 16 + TypeScript frontend
packages/shared/ Shared types, zod schemas, constants
```

## Commands


## Phase status


## Architecture rules

## LLM providers

Cloudflare is used for **embeddings only** (`EMBEDDING_PROVIDER=cloudflare`). It is
**not** an LLM provider. The user-facing chat role is intentionally unwired (HTTP
501 "LLM is not wired up").

| Provider | Env | Notes |
|---|---|---|
| `stub` | `LLM_PROVIDER=stub` | Heuristic-only. Works end-to-end but low quality. |
| `gemini` | `LLM_PROVIDER=gemini` or `routing` + `GEMINI_API_KEY` | Primary for structured extraction/audit under `routing`; JSON mode (`responseMimeType: application/json`). |
| `routing` | `LLM_PROVIDER=routing` | Per-role fallback chains. extract/audit: cerebras → gemini → groq → stub. chat: cerebras → groq → gemini → stub (unused until chat is wired). |
| `fireworks` | `LLM_PROVIDER=fireworks` + `FIREWORKS_API_KEY` | OpenAI-compatible. JSON mode for structured output. |

## Web frontend conventions


## Testing

- **Zero errors** in tests, typecheck, lint, and builds is required before any feature is considered done.
- **Warnings are acceptable** unless they are security-critical (e.g. known-vulnerability advisories, hardcoded secrets, unsafe deserialization). Non-critical lint/style warnings (unused vars, import-ordering hints, blind-exception catches with an explicit fallback) do not block completion. Do not chase "zero warnings" — prefer production-ready, readable code over silencing linters.



## What NOT to do

