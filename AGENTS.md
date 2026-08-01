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

| Provider | Env | Notes |
|---|---|---|
| `stub` | `LLM_PROVIDER=stub` | Heuristic-only. Works end-to-end but low quality. |
| `cloudflare` | `LLM_PROVIDER=cloudflare` + CF credentials | Workers AI. Already wired. |
| `fireworks` | `LLM_PROVIDER=fireworks` + `FIREWORKS_API_KEY` | OpenAI-compatible. JSON mode for structured output. **Recommended for Phase 3 audit.** |

## Web frontend conventions


## Testing



## What NOT to do

