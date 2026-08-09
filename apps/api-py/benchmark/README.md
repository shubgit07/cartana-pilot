# PR Drift-Detection Benchmark

Measures how accurately the decomposed PR Trust Brief **Stage 2 verifier**
(`_run_stage2_verification`) classifies each requirement as `covered`,
`partial`, or `missing` relative to a hand-labelled fixture set.

**The pipeline is LLM-only by design.** Since the "no heuristics" wiring, Stage 2
and Stage 3 never fall back to keyword matching: if the LLM cannot produce
parseable structured verdicts, the request fails loudly with an
`LLMServiceError` (HTTP 502) instead of returning fabricated results. A PR whose
LLM call fails is recorded as `LLM FAILED` (all requirements `unclear`) in the
report and counts as 0% accurate.

## How it runs

The harness drives the **exact production code path** used by
`POST /audit/verify-pr`:

1. Requirements are loaded from `fixtures/ground_truth.json` (hand-labelled;
   the LLM extraction step is intentionally skipped to keep the measurement
   focused on drift detection).
2. Each diff in `fixtures/prs/` is parsed with the real `parse_unified_diff`.
3. Verdicts come from the unmodified `_run_stage2_verification` function, which
   calls `provider._structured(...)` and raises `LLMServiceError` on failure.

## Running

From `apps/api-py`:

```bash
# Real LLM via the routing chain (cerebras -> gemini -> groq)
uv run python benchmark/eval_drift.py            # LLM_PROVIDER=routing

# Or pin a single provider
LLM_PROVIDER=gemini uv run python benchmark/eval_drift.py
```

LLM runs require the relevant API keys in `.env` (see `apps/api-py` env
settings).

> `--provider stub` is **not** a meaningful baseline anymore: the stub provider
> has no LLM, so it now fails every PR with `LLMServiceError` rather than
> fabricating verdicts. That's the intended behavior — a trust brief must never
> be produced from keyword heuristics.

## Output

- Console table: per-PR accuracy, per-class precision/recall/F1, overall
  accuracy, macro-F1, weighted-F1, and per-PR `LLM FAILED` markers.
- `reports/<provider>_<timestamp>.json`: full predictions, confusion matrix,
  errors, and metrics for regression tracking (gitignored).

## Fixtures

`fixtures/spec_brief.md` — the "Project Atlas" PRD (6 requirements).
`fixtures/ground_truth.json` — requirements + per-PR expected statuses.

| PR diff | Intent | Notable cases |
|---|---|---|
| `full_impl.diff` | All 6 requirements implemented | Trivially covered |
| `missing_r4.diff` | Notifications omitted | Drift must be caught |
| `partial_r2.diff` | Task update/delete missing | Partial must be caught |
| `renamed_impl.diff` | Auth implemented with different vocabulary | Vocabulary robustness |
| `tests_only.diff` | Tests but no implementation | All missing |
| `unrelated_refactor.diff` | Infrastructure only | All missing |

The keyword heuristic (now removed) failed on `missing_r4.diff` (sibling files
share words like "task"/"assigned") and `renamed_impl.diff` (different naming) —
exactly the failure mode JSON-mode LLM verification fixes.
