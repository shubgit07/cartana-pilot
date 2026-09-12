"""Drift-detection accuracy eval for the PR Trust Brief Stage 2 verifier.

Measures how well the Stage 2 requirement-vs-diff verifier classifies
requirements as covered / partial / missing against a hand-labelled fixture
set, across the configured LLM provider (default: ``LLM_PROVIDER=routing``).

Usage (from ``apps/api-py``):

    uv run python benchmark/eval_drift.py                # routing (default), all PRs
    uv run python benchmark/eval_drift.py --provider stub

To avoid free-tier LLM rate limits (RPM/RPD), evaluate one diff per invocation
(one LLM call each) and merge the per-PR reports afterwards:

    uv run python benchmark/eval_drift.py --provider gemini --prs full_impl.diff
    uv run python benchmark/eval_drift.py --provider gemini --prs missing_r4.diff
    # ... one command per PR, paced however you like ...
    uv run python benchmark/eval_drift.py --provider gemini --merge

The eval drives the exact production code path used by
``POST /audit/verify-pr``: requirements are the ground-truth fixtures, the diff
is parsed with ``parse_unified_diff``, and verdicts come from the unmodified
``_run_stage2_verification`` function. Reports are written to
``benchmark/reports/``.
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

STATUSES = ("covered", "partial", "missing")


def _load_fixtures() -> dict[str, Any]:
    ground_truth = json.loads((FIXTURES_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    spec_text = (FIXTURES_DIR / ground_truth["spec_file"]).read_text(encoding="utf-8")
    return {
        "ground_truth": ground_truth,
        "spec_text": spec_text,
        "requirements": ground_truth["requirements"],
        "prs": ground_truth["prs"],
    }


def _build_provider():
    from app.providers.ai_provider import get_ai_provider

    provider = get_ai_provider()
    if provider.__class__.__name__ == "StubAIProvider":
        raise SystemExit(
            "ERROR: provider resolved to StubAIProvider (no real LLM configured). "
            "The eval cannot measure LLM drift detection without an LLM. "
            "Pass `--provider routing` or set LLM_PROVIDER to a real provider "
            "(routing, gemini, groq, fireworks)."
        )
    return provider


def _parse_diff(diff_raw: str) -> tuple[list[dict[str, Any]], str]:
    from app.core.diff_parser import parse_unified_diff

    parsed = parse_unified_diff(diff_raw)
    changed_files = [
        {"filename": f.filename, "status": f.status, "additions": f.additions, "deletions": f.deletions}
        for f in parsed.files
    ]
    return changed_files, parsed.compressed_text


def _run_verification(
    provider,
    reqs: list[dict[str, Any]],
    diff_raw: str,
    *,
    diagnostics: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    from app.core.workflow.pr_verification_graph import _run_stage2_verification

    changed_files, compressed_text = _parse_diff(diff_raw)
    verdicts = _run_stage2_verification(
        provider, reqs, changed_files, compressed_text, diagnostics=diagnostics
    )
    return [
        {
            "reqId": v.reqId,
            "predicted": v.status,
            "confidence": v.confidence,
            "evidenceFile": v.evidenceFile or "",
        }
        for v in verdicts
    ]


def _score_predictions(pred_by_pr: dict[str, dict[str, str]], truth: dict[str, dict[str, str]]) -> dict[str, Any]:
    matrix = {exp: {pred: 0 for pred in STATUSES} for exp in STATUSES}
    per_pr: dict[str, dict[str, Any]] = {}

    for pr_name, rows in truth.items():
        correct = total = 0
        for req_id, expected in rows.items():
            predicted = pred_by_pr.get(pr_name, {}).get(req_id, "unclear")
            if predicted not in STATUSES:
                predicted = "missing"
            matrix[expected][predicted] += 1
            total += 1
            if predicted == expected:
                correct += 1
        per_pr[pr_name] = {"correct": correct, "total": total, "accuracy": correct / total if total else 0.0}

    def _safe_ratio(num: float, den: float) -> float:
        return num / den if den else 0.0

    per_class: dict[str, dict[str, Any]] = {}
    for s in STATUSES:
        support = sum(matrix[s].values())
        tp = matrix[s][s]
        fp = sum(matrix[o][s] for o in STATUSES if o != s)
        precision = _safe_ratio(tp, tp + fp)
        recall = _safe_ratio(tp, support)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        per_class[s] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    total_pred = sum(per_class[s]["support"] for s in STATUSES)
    macro_f1 = sum(per_class[s]["f1"] for s in STATUSES) / len(STATUSES)
    weighted_f1 = sum(per_class[s]["f1"] * per_class[s]["support"] for s in STATUSES) / total_pred if total_pred else 0.0
    overall_acc = sum(matrix[s][s] for s in STATUSES) / total_pred if total_pred else 0.0

    return {
        "confusion_matrix": [[matrix[e][p] for p in STATUSES] for e in STATUSES],
        "per_class": per_class,
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "accuracy": round(overall_acc, 4),
        "per_pr": per_pr,
    }


def _pretty_table(scores: dict[str, Any]) -> str:
    lines = ["", "Per-PR accuracy:", "  " + "  ".join(f"{p:>12}" for p in scores["per_pr"])]
    rows = [f"{'pr':<22} {'correct':>8} {'total':>6} {'acc':>7}"]
    for name, stat in scores["per_pr"].items():
        rows.append(f"{name:<22} {stat['correct']:>8} {stat['total']:>6} {stat['accuracy']:>7.2%}")
    lines.append("  " + "\n  ".join(rows))

    lines.append("Per-class metrics (precision / recall / F1):")
    for s, m in scores["per_class"].items():
        lines.append(f"  {s:<10} p={m['precision']:.3f} r={m['recall']:.3f} f1={m['f1']:.3f} (n={m['support']})")

    lines.append(f"Overall accuracy: {scores['accuracy']:.2%}")
    lines.append(f"Macro-F1:         {scores['macro_f1']:.3f}")
    lines.append(f"Weighted-F1:      {scores['weighted_f1']:.3f}")
    return "\n".join(lines)


def _merge_reports() -> int:
    """Combine per-PR reports into a single score table (no LLM calls)."""
    fixtures = _load_fixtures()
    pred_by_pr: dict[str, dict[str, str]] = {}
    raw_responses: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    seen: dict[str, str] = {}

    for path in sorted(REPORTS_DIR.glob("*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(report, dict) or "pr" not in report:
            continue
        pr = report["pr"]
        if pr not in fixtures["prs"]:
            continue
        generated = report.get("generated_at", "")
        if pr in seen and generated <= seen[pr]:
            continue
        seen[pr] = generated
        pred_by_pr[pr] = report.get("predictions", {}).get(pr, {})
        raw_responses[pr] = report.get("raw_responses", {}).get(pr, {})
        pr_errors = report.get("errors", {})
        if pr_errors:
            errors[pr] = pr_errors.get(pr, "")

    if not pred_by_pr:
        print("No per-PR reports found in reports/. Run with `--prs <name>` first.")
        return 1

    scores = _score_predictions(pred_by_pr, fixtures["prs"])
    scores["errors"] = errors
    print(f"Merged {len(pred_by_pr)} per-PR reports:")
    print(_pretty_table(scores))

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    provider_name = "merged"
    report_path = REPORTS_DIR / f"{provider_name}_{timestamp}.json"
    report = {
        "generated_at": timestamp,
        "provider": provider_name,
        "llm_provider_env": os.environ.get("LLM_PROVIDER", "unset"),
        "merged_from": {pr: gen for pr, gen in seen.items()},
        "scores": scores,
        "predictions": pred_by_pr,
        "raw_responses": raw_responses,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {report_path}")
    return 0


def _write_per_pr_report(
    provider,
    timestamp: str,
    pr_name: str,
    predictions: dict[str, str],
    raw_response: dict[str, Any],
    errors: dict[str, str],
) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    safe_name = Path(pr_name).stem
    provider_name = provider.__class__.__name__.lower()
    report = {
        "generated_at": timestamp,
        "provider": provider_name,
        "llm_provider_env": os.environ.get("LLM_PROVIDER", "unset"),
        "pr": pr_name,
        "predictions": {pr_name: predictions},
        "raw_responses": {pr_name: raw_response},
        "errors": {pr_name: errors.get(pr_name, "")} if errors.get(pr_name) else {},
    }
    path = REPORTS_DIR / f"{provider_name}_{timestamp}_{safe_name}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default=None, help="Override LLM_PROVIDER (e.g. stub, routing).")
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="Seconds to pause between PR evaluations (default: 2.0). "
        "Larger values reduce free-tier LLM rate-limit (429) risk.",
    )
    parser.add_argument(
        "--prs",
        nargs="+",
        default=None,
        metavar="PR",
        help="Evaluate only the named PR diffs (one LLM call each), writing a per-PR report per diff.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge existing per-PR reports into a combined score table (no LLM calls).",
    )
    args = parser.parse_args()

    if args.merge:
        return _merge_reports()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    fixtures = _load_fixtures()
    provider = _build_provider()

    available = sorted(fixtures["prs"])
    if args.prs:
        unknown = [p for p in args.prs if p not in available]
        if unknown:
            raise SystemExit(f"ERROR: unknown PR(s): {', '.join(unknown)}. Available: {', '.join(available)}")
        pr_names = args.prs
    else:
        pr_names = available

    print(f"Provider: {provider.__class__.__name__}")
    print(f"Fixtures: {len(fixtures['requirements'])} requirements x {len(pr_names)} PR diffs\n")

    pred_by_pr: dict[str, dict[str, str]] = {}
    errors: dict[str, str] = {}
    raw_responses: dict[str, dict[str, Any]] = {}
    for pr_name in pr_names:
        diff_raw = (FIXTURES_DIR / "prs" / pr_name).read_text(encoding="utf-8")
        diagnostics: dict[str, Any] = {}
        try:
            results = _run_verification(
                provider, fixtures["requirements"], diff_raw, diagnostics=diagnostics
            )
        except Exception as exc:  # noqa: BLE001
            errors[pr_name] = f"{type(exc).__name__}: {exc}"
            pred_by_pr[pr_name] = {r["id"]: "unclear" for r in fixtures["requirements"]}
            diagnostics.setdefault("error", errors[pr_name])
            print(f"  {pr_name}: LLM FAILED -> {type(exc).__name__} ({str(exc)[:100]})")
        else:
            pred_by_pr[pr_name] = {r["reqId"]: r["predicted"] for r in results}
            raw_responses[pr_name] = diagnostics
            print(f"  {pr_name}: " + ", ".join(f"{r['reqId']}={r['predicted']}" for r in results))
        time.sleep(args.sleep)

    if args.prs:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        for pr_name in pr_names:
            path = _write_per_pr_report(
                provider,
                timestamp,
                pr_name,
                pred_by_pr.get(pr_name, {r["id"]: "unclear" for r in fixtures["requirements"]}),
                raw_responses.get(pr_name, {}),
                errors,
            )
            print(f"  per-PR report: {path}")
        return 0

    scores = _score_predictions(pred_by_pr, fixtures["prs"])
    scores["errors"] = errors
    print(_pretty_table(scores))

    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    provider_name = provider.__class__.__name__.lower()
    report_path = REPORTS_DIR / f"{provider_name}_{timestamp}.json"
    report = {
        "generated_at": timestamp,
        "provider": provider_name,
        "llm_provider_env": os.environ.get("LLM_PROVIDER", "unset"),
        "scores": scores,
        "predictions": pred_by_pr,
        "raw_responses": raw_responses,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
