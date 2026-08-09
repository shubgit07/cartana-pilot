"""B2 — Coverage-audit re-retrieval A/B eval.

Measures the false-"missing" reduction from the confidence-triggered
re-retrieval pass on the requirement<->task coverage audit.

Two modes are evaluated per scenario against the same fixture:
  - ``baseline``     : top-k=5 embedding retrieval + one LLM classification, no re-check
  - ``reretrieval``  : same, plus one wider (top-k=10) re-retrieval + re-classification
                       for requirements judged ``missing``/``unclear``

Metrics: false-"missing" count per mode, % reduction, missing-class precision/recall.

The harness drives the **real** production functions
(``audit_service._select_candidate_tasks`` and ``audit_service._judge_coverage``),
so the measured numbers reflect the code that runs in ``POST /projects/:id/audit/run``.

Usage (from ``apps/api-py``):

    uv run python benchmark/eval_reretrieval.py                # routing (default), all scenarios
    uv run python benchmark/eval_reretrieval.py --provider stub   # dry run against stub

To avoid free-tier LLM rate limits, evaluate one scenario per invocation and
merge the per-scenario reports afterwards:

    uv run python benchmark/eval_reretrieval.py --provider routing --scenarios different_vocab
    uv run python benchmark/eval_reretrieval.py --provider routing --scenarios distractor
    # ... one command per scenario, paced however you like ...
    uv run python benchmark/eval_reretrieval.py --merge

Env: ``LLM_PROVIDER=routing`` (audit role routes to ``gemini_audit_model``,
default ``gemini-3.5-flash-lite``), ``EMBEDDING_PROVIDER=cloudflare`` for real
embeddings. Reports are written to ``benchmark/reports/``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

dotenv.load_dotenv(REPO_ROOT / ".env")

BENCH_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BENCH_DIR / "fixtures"
REPORTS_DIR = BENCH_DIR / "reports"

STATUSES = ("covered", "partial", "missing", "unclear")
TOP_K = 5
RERETRIEVE_K = TOP_K * 2

# Gemini free-tier audit model (gemini-3.5-flash-lite) is limited to 15 RPM.
# Space every LLM call >=4s apart so a scenario burst stays under the limit.
MIN_LLM_INTERVAL_SECONDS = 4.0

import threading

_PACE_LOCK = threading.Lock()
_LAST_LLM_CALL_TS: float = 0.0


def _pace_llm_call() -> None:
    """Sleep so consecutive LLM calls are >= MIN_LLM_INTERVAL_SECONDS apart."""
    global _LAST_LLM_CALL_TS
    with _PACE_LOCK:
        now = time.monotonic()
        wait = MIN_LLM_INTERVAL_SECONDS - (now - _LAST_LLM_CALL_TS)
        if wait > 0:
            time.sleep(wait)
            now = time.monotonic()
        _LAST_LLM_CALL_TS = now


def _load_fixtures() -> dict[str, Any]:
    ground_truth = json.loads(
        (FIXTURES_DIR / "coverage_ground_truth.json").read_text(encoding="utf-8")
    )
    return {
        "ground_truth": ground_truth,
        "requirements": ground_truth["requirements"],
        "scenarios": ground_truth["scenarios"],
    }


def _build_provider():
    from app.providers.ai_provider import get_ai_provider

    provider = get_ai_provider()
    if provider.__class__.__name__ == "StubAIProvider":
        raise SystemExit(
            "ERROR: provider resolved to StubAIProvider (no real LLM configured). "
            "The eval cannot measure coverage classification without an LLM. "
            "Set LLM_PROVIDER=routing and GEMINI_API_KEY (audit role uses "
            "gemini_audit_model), or pass a real provider via --provider."
        )
    return provider


def _fake_task(task: dict[str, Any]):
    """Build a Task-like object (title/description/id only) for the pure retriever."""
    from types import SimpleNamespace

    return SimpleNamespace(
        id=task["id"],
        title=task["title"],
        description=task.get("description", ""),
    )


def _classify(
    provider,
    req: dict[str, Any],
    tasks: list[Any],
    *,
    top_k: int,
) -> tuple[str, list[str]]:
    """Run retrieval + classification for one requirement. Returns (status, candidate_ids)."""
    from app.api.services.audit_service import (
        _judge_coverage,
        _overall_status,
        _select_candidate_tasks,
    )
    from app.providers.ai_provider import AIAuditCoverageInput

    req_text = f"{req['title']} {req['description'] or ''}"
    candidates = _select_candidate_tasks(req_text, tasks, top_k=top_k)
    if not candidates:
        return "missing", []

    _pace_llm_call()
    judgments = _judge_coverage(provider, AIAuditCoverageInput(
        requirement={"title": req["title"], "description": req["description"] or ""},
        candidateTasks=[
            {"title": t.title, "description": t.description or ""} for t in candidates
        ],
    ))
    return _overall_status([j.status for j in judgments]), [t.id for t in candidates]


def _run_scenario(
    provider,
    scenario: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mirror production: one initial classification; a wider re-check (top_k*2) only
    for requirements judged ``missing``/``unclear``, keeping the better verdict."""
    from app.api.services.audit_service import _status_rank

    tasks = [_fake_task(t) for t in scenario["tasks"]]
    expected = scenario["expected"]

    baseline: dict[str, str] = {}
    reretrieval: dict[str, str] = {}
    rescues: list[str] = []

    for req in requirements:
        req_id = req["id"]

        base_status, _ = _classify(provider, req, tasks, top_k=TOP_K)
        baseline[req_id] = base_status

        rr_status = base_status
        if base_status in ("missing", "unclear"):
            retry_status, _ = _classify(provider, req, tasks, top_k=RERETRIEVE_K)
            if _status_rank(retry_status) > _status_rank(base_status):
                rr_status = retry_status
        reretrieval[req_id] = rr_status

        if base_status in ("missing", "unclear") and rr_status in ("covered", "partial"):
            rescues.append(req_id)

    return {
        "expected": expected,
        "baseline": baseline,
        "reretrieval": reretrieval,
        "rescues": rescues,
    }


def _count_false_missing(pred: dict[str, str], expected: dict[str, str]) -> int:
    """A false 'missing' is any requirement labeled missing but expected non-missing."""
    return sum(
        1 for req_id, exp in expected.items() if pred.get(req_id) == "missing" and exp != "missing"
    )


def _missing_metrics(pred: dict[str, str], expected: dict[str, str]) -> dict[str, Any]:
    tp = sum(1 for r, e in expected.items() if pred.get(r) == "missing" and e == "missing")
    fp = _count_false_missing(pred, expected)
    fn = sum(1 for r, e in expected.items() if pred.get(r) != "missing" and e == "missing")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "true_missing": tp,
        "false_missing": fp,
        "missed_missing": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def _score(mode_results: dict[str, dict[str, Any]], mode: str) -> dict[str, Any]:
    total_false_missing = 0
    per_scenario: dict[str, dict[str, Any]] = {}
    merged_pred: dict[str, str] = {}
    merged_expected: dict[str, str] = {}

    for name, result in mode_results.items():
        pred = result[mode]
        expected = result["expected"]
        false_missing = _count_false_missing(pred, expected)
        total_false_missing += false_missing
        per_scenario[name] = {
            "predictions": pred,
            "false_missing": false_missing,
            "rescues": result.get("rescues", []),
        }
        merged_pred.update(pred)
        merged_expected.update(expected)

    return {
        "total_false_missing": total_false_missing,
        "missing_metrics": _missing_metrics(merged_pred, merged_expected),
        "per_scenario": per_scenario,
    }


def _pretty_table(
    baseline_scores: dict[str, Any],
    reretrieval_scores: dict[str, Any],
) -> str:
    lines = [""]

    b_fm = baseline_scores["total_false_missing"]
    r_fm = reretrieval_scores["total_false_missing"]
    reduction = (b_fm - r_fm) / b_fm if b_fm else 0.0
    b_metrics = baseline_scores["missing_metrics"]
    r_metrics = reretrieval_scores["missing_metrics"]

    rows = [f"{'scenario':<22} {'base_FM':>8} {'rr_FM':>8} {'rescues':>8}"]
    for name in baseline_scores["per_scenario"]:
        rows.append(
            f"{name:<22} "
            f"{baseline_scores['per_scenario'][name]['false_missing']:>8} "
            f"{reretrieval_scores['per_scenario'][name]['false_missing']:>8} "
            f"{len(reretrieval_scores['per_scenario'][name].get('rescues', [])):>8}"
        )
    lines.append("  " + "\n  ".join(rows))
    lines.append("")
    lines.append(f"False-'missing' count:  baseline={b_fm}  reretrieval={r_fm}")
    lines.append(f"False-'missing' reduction: {reduction:.2%}")
    lines.append(
        f"Missing precision/recall: baseline={b_metrics['precision']:.3f}/{b_metrics['recall']:.3f} "
        f"reretrieval={r_metrics['precision']:.3f}/{r_metrics['recall']:.3f}"
    )
    return "\n".join(lines)


def _merge_reports() -> int:
    fixtures = _load_fixtures()
    scenarios = fixtures["scenarios"]
    merged: dict[str, dict[str, Any]] = {}
    seen: dict[str, str] = {}

    for path in sorted(REPORTS_DIR.glob("*reretrieval*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(report, dict) or "scenario" not in report:
            continue
        name = report["scenario"]
        if name not in scenarios:
            continue
        generated = report.get("generated_at", "")
        if name in seen and generated <= seen[name]:
            continue
        seen[name] = generated
        merged[name] = report["results"]

    if not merged:
        print("No per-scenario re-retrieval reports found in reports/.")
        return 1

    baseline_scores = _score(merged, "baseline")
    reretrieval_scores = _score(merged, "reretrieval")

    print(f"Merged {len(merged)} per-scenario reports:")
    print(_pretty_table(baseline_scores, reretrieval_scores))

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"merged_reretrieval_{timestamp}.json"
    report = {
        "generated_at": timestamp,
        "kind": "reretrieval_ab",
        "llm_provider_env": os.environ.get("LLM_PROVIDER", "unset"),
        "merged_from": {name: gen for name, gen in seen.items()},
        "baseline": baseline_scores,
        "reretrieval": reretrieval_scores,
        "per_scenario": {
            name: {
                "expected": merged[name]["expected"],
                "baseline": merged[name]["baseline"],
                "reretrieval": merged[name]["reretrieval"],
                "rescues": merged[name]["rescues"],
            }
            for name in merged
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {report_path}")
    return 0


def _write_scenario_report(
    provider,
    timestamp: str,
    scenario_name: str,
    results: dict[str, Any],
    errors: dict[str, str],
) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    provider_name = provider.__class__.__name__.lower()
    report = {
        "generated_at": timestamp,
        "kind": "reretrieval_ab",
        "provider": provider_name,
        "llm_provider_env": os.environ.get("LLM_PROVIDER", "unset"),
        "scenario": scenario_name,
        "results": results,
        "errors": errors,
    }
    path = REPORTS_DIR / f"{provider_name}_{timestamp}_reretrieval_{scenario_name}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default=None, help="Override LLM_PROVIDER (e.g. routing).")
    parser.add_argument(
        "--sleep",
        type=float,
        default=8.0,
        help="Seconds to pause between scenario evaluations (default: 8.0). "
        "Pacing protects free-tier LLM RPM/RPD limits.",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=None,
        metavar="SCENARIO",
        help="Evaluate only the named scenarios, writing a per-scenario report each.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge existing per-scenario reports into a combined A/B table (no LLM calls).",
    )
    args = parser.parse_args()

    if args.merge:
        return _merge_reports()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    fixtures = _load_fixtures()
    provider = _build_provider()

    available = sorted(fixtures["scenarios"])
    if args.scenarios:
        unknown = [s for s in args.scenarios if s not in available]
        if unknown:
            raise SystemExit(
                f"ERROR: unknown scenario(s): {', '.join(unknown)}. Available: {', '.join(available)}"
            )
        scenario_names = args.scenarios
    else:
        scenario_names = available

    print(f"Provider: {provider.__class__.__name__}")
    print(
        f"Fixtures: {len(fixtures['requirements'])} requirements x {len(scenario_names)} scenarios\n"
    )

    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for name in scenario_names:
        scenario = fixtures["scenarios"][name]
        try:
            result = _run_scenario(provider, scenario, fixtures["requirements"])
        except Exception as exc:  # noqa: BLE001
            errors[name] = f"{type(exc).__name__}: {exc}"
            print(f"  {name}: FAILED -> {type(exc).__name__} ({str(exc)[:100]})")
            time.sleep(args.sleep)
            continue

        results[name] = result
        print(
            f"  {name}: baseline="
            + ", ".join(f"{r}={s}" for r, s in result["baseline"].items())
            + " | reretrieval="
            + ", ".join(f"{r}={s}" for r, s in result["reretrieval"].items())
            + (f" | rescues={result['rescues']}" if result["rescues"] else "")
        )
        time.sleep(args.sleep)

    if args.scenarios:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        for name in scenario_names:
            if name not in results:
                continue
            path = _write_scenario_report(provider, timestamp, name, results[name], errors)
            print(f"  per-scenario report: {path}")
        return 0

    baseline_scores = _score(results, "baseline")
    reretrieval_scores = _score(results, "reretrieval")
    print(_pretty_table(baseline_scores, reretrieval_scores))

    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    provider_name = provider.__class__.__name__.lower()
    report_path = REPORTS_DIR / f"{provider_name}_{timestamp}_reretrieval.json"
    report = {
        "generated_at": timestamp,
        "kind": "reretrieval_ab",
        "provider": provider_name,
        "llm_provider_env": os.environ.get("LLM_PROVIDER", "unset"),
        "baseline": baseline_scores,
        "reretrieval": reretrieval_scores,
        "per_scenario": {
            name: {
                "expected": results[name]["expected"],
                "baseline": results[name]["baseline"],
                "reretrieval": results[name]["reretrieval"],
                "rescues": results[name]["rescues"],
            }
            for name in results
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
