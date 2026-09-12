"""Stateful LangGraph PR Trust Brief Verification Workflow.

Orchestrates the multi-stage PR verification pipeline:
  START -> check_cache -> [hit? END : extract_spec]
        -> clean_diff
        -> code_verifier (Stage 2 LLM Call)
        -> risk_analyst (Stage 3 LLM Call)
        -> persist_and_cache
        -> END
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.api.schemas.audit import (
    ChangedFileSummary,
    PRRiskAlert,
    PRTrustBrief,
    RequirementVerificationVerdict,
)
from app.core.clean_text import clean_document_text
from app.core.diff_parser import parse_unified_diff
from app.core.errors import LLMServiceError, ValidationError
from app.providers.ai_provider import (
    AIChatInput,
    _safe_json_loads,
    get_ai_provider,
)
from app.providers.cache_provider import cache_audit, get_cached_audit
from app.providers.prompts.pr_audit import (
    build_pr_risk_summary_prompt,
    build_pr_verification_prompt,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------


class PRVerificationState(TypedDict, total=False):
    # Context / Identifiers
    project_id: str
    user_id: str
    spec_text: str
    raw_diff: str
    pr_url: str | None
    db: Session | None

    # Cache / Hashes
    spec_hash: str
    diff_hash: str
    cache_hit: bool

    # Stage 1: Processed & Filtered Inputs
    requirements: list[dict[str, Any]]
    changed_files: list[dict[str, Any]]
    changed_files_summary: list[ChangedFileSummary]
    compressed_diff: str
    repo_context: str

    # Stage 2: Verification Verdicts
    verdicts: list[RequirementVerificationVerdict]

    # Stage 3: Risk & Trust Analysis
    coverage_score: int
    trust_level: str
    summary_text: str
    risk_alerts: list[PRRiskAlert]

    # Final Result
    final_brief: PRTrustBrief | None
    error: str | None


# ---------------------------------------------------------------------------
# LLM Stage Helpers
# ---------------------------------------------------------------------------


def _parse_verdicts(raw_json: str | None, *, label: str) -> list[dict[str, Any]]:
    """Parse a Stage 2 verdicts payload; [] when empty or unparseable."""
    if not raw_json:
        return []
    try:
        parsed = _safe_json_loads(raw_json, label=label)
    except Exception as e:  # noqa: BLE001
        logger.warning("%s output was not valid JSON: %s", label, e)
        return []
    if isinstance(parsed, dict):
        return parsed.get("verdicts", [])
    return []


def _run_stage2_verification(
    provider: Any,
    reqs: list[dict[str, Any]],
    changed_files: list[dict[str, Any]],
    diff_hunks: str,
    repo_context: str = "",
) -> list[RequirementVerificationVerdict]:
    """Stage 2: Strict Code Verifier (LLM Call 1)."""
    system_prompt, user_prompt = build_pr_verification_prompt(
        reqs, changed_files, diff_hunks, repo_context
    )
    verdicts_data: list[dict[str, Any]] = []

    if hasattr(provider, "_structured"):
        raw_json: str | None = None
        try:
            raw_json = provider._structured(system_prompt, user_prompt, max_tokens=6000, temperature=0.1)
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 2 structured LLM call failed: %s", e)
        verdicts_data = _parse_verdicts(raw_json, label="Stage 2 Verification")

    if not verdicts_data and hasattr(provider, "chat"):
        try:
            chat_out = provider.chat(AIChatInput(question=f"{system_prompt}\n\n{user_prompt}", history=[], passages=[]))
            verdicts_data = _parse_verdicts(chat_out.answer, label="Stage 2 Verification (chat)")
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 2 chat LLM call failed: %s", e)

    if verdicts_data:
        verdicts: list[RequirementVerificationVerdict] = []
        for v in verdicts_data:
            status_val = v.get("status", "unclear")
            if status_val not in ("covered", "partial", "missing", "unclear"):
                status_val = "unclear"
            conf_val = v.get("confidence", "high")
            if conf_val not in ("high", "medium", "low"):
                conf_val = "high"

            verdicts.append(RequirementVerificationVerdict(
                reqId=str(v.get("reqId", "R?")),
                title=str(v.get("title", "")),
                status=status_val,
                confidence=conf_val,
                evidenceFile=v.get("evidenceFile"),
                evidenceSnippet=v.get("evidenceSnippet"),
                rationale=str(v.get("rationale", "")),
            ))
        return verdicts

    raise LLMServiceError(
        "Stage 2 verification failed: the LLM did not return valid verdicts. "
        "Check that an LLM provider is configured (LLM_PROVIDER != stub) and "
        "that the provider's structured output is parseable."
    )


def _parse_risk_analysis(raw_json: str | None, *, label: str) -> dict[str, Any] | None:
    """Parse a Stage 3 risk/trust payload; None when empty or unparseable."""
    if not raw_json:
        return None
    try:
        parsed = _safe_json_loads(raw_json, label=label)
    except Exception as e:  # noqa: BLE001
        logger.warning("%s output was not valid JSON: %s", label, e)
        return None
    if isinstance(parsed, dict) and "coverageScore" in parsed:
        return parsed
    return None


def _run_stage3_risk_analysis(
    provider: Any,
    verdicts: list[RequirementVerificationVerdict],
    changed_files: list[dict[str, Any]],
) -> tuple[int, str, str, list[PRRiskAlert]]:
    """Stage 3: Risk, Security & Trust Analyst (LLM Call 2)."""
    verdicts_dict = [v.model_dump() for v in verdicts]
    system_prompt, user_prompt = build_pr_risk_summary_prompt(verdicts_dict, changed_files)
    parsed: dict[str, Any] | None = None

    if hasattr(provider, "_structured"):
        raw_json: str | None = None
        try:
            raw_json = provider._structured(system_prompt, user_prompt, max_tokens=3000, temperature=0.2)
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 3 structured LLM call failed: %s", e)
        parsed = _parse_risk_analysis(raw_json, label="Stage 3 Risk Analysis")

    if parsed is None and hasattr(provider, "chat"):
        try:
            chat_out = provider.chat(AIChatInput(question=f"{system_prompt}\n\n{user_prompt}", history=[], passages=[]))
            parsed = _parse_risk_analysis(chat_out.answer, label="Stage 3 Risk Analysis (chat)")
        except Exception as e:  # noqa: BLE001
            logger.warning("Stage 3 chat LLM call failed: %s", e)

    if parsed is not None:
        alerts: list[PRRiskAlert] = []
        for a in parsed.get("riskAlerts", []):
            kind_val = a.get("kind", "security_gap")
            if kind_val not in ("missing_backend_check", "no_tests", "scope_creep", "security_gap", "error_handling"):
                kind_val = "security_gap"
            sev_val = a.get("severity", "warning")
            if sev_val not in ("critical", "warning", "info"):
                sev_val = "warning"
            alerts.append(PRRiskAlert(
                kind=kind_val,
                severity=sev_val,
                title=str(a.get("title", "")),
                description=str(a.get("description", "")),
                affectedFiles=[str(f) for f in a.get("affectedFiles", [])],
            ))

        trust_val = str(parsed.get("trustLevel", "medium")).lower()
        if trust_val not in ("high", "medium", "low"):
            trust_val = "medium"

        return (
            int(parsed.get("coverageScore", 0)),
            trust_val,
            str(parsed.get("summary", "")),
            alerts,
        )

    raise LLMServiceError(
        "Stage 3 risk analysis failed: the LLM did not return a valid trust "
        "brief. Check that an LLM provider is configured (LLM_PROVIDER != stub) "
        "and that the provider's structured output is parseable."
    )


# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------


def check_cache_node(state: PRVerificationState) -> dict[str, Any]:
    """Node 1: Check Redis SHA-256 deduplication cache."""
    spec_raw = (state.get("spec_text") or "").strip()
    diff_raw = (state.get("raw_diff") or "").strip()

    spec_hash = hashlib.sha256(spec_raw.encode("utf-8")).hexdigest()[:16]
    diff_hash = hashlib.sha256(diff_raw.encode("utf-8")).hexdigest()[:16]

    cached = get_cached_audit(spec_hash, diff_hash)
    if cached:
        logger.info("LangGraph Node [check_cache]: Cache hit for spec_hash=%s, diff_hash=%s", spec_hash, diff_hash)
        return {
            "spec_hash": spec_hash,
            "diff_hash": diff_hash,
            "cache_hit": True,
            "final_brief": PRTrustBrief(**cached),
        }

    return {
        "spec_hash": spec_hash,
        "diff_hash": diff_hash,
        "cache_hit": False,
    }


def extract_spec_node(state: PRVerificationState) -> dict[str, Any]:
    """Node 2: Clean and extract requirements from spec text if not already populated."""
    reqs: list[dict[str, Any]] = list(state.get("requirements") or [])

    if not reqs:
        spec_raw = (state.get("spec_text") or "").strip()
        if spec_raw:
            from app.api.services.input_service import extract_requirements_with_llm

            cleaned_spec = clean_document_text(spec_raw)
            extracted = extract_requirements_with_llm(cleaned_spec)
            for item in extracted:
                reqs.append({
                    "id": item.req_id,
                    "title": item.title,
                    "description": item.description,
                    "kind": item.kind,
                })

    if not reqs:
        raise ValidationError("No requirements found. Please provide a spec text or upload a project document.")

    return {"requirements": reqs}


def clean_diff_node(state: PRVerificationState) -> dict[str, Any]:
    """Node 3: Deterministic diff parsing, noise filtering, and hunk compression."""
    diff_raw = (state.get("raw_diff") or "").strip()
    if not diff_raw:
        raise ValidationError("No git diff provided. Please paste a unified diff or provide a valid GitHub PR URL.")

    parsed_diff = parse_unified_diff(diff_raw)
    changed_files_summary = [
        ChangedFileSummary(
            filename=f.filename,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
        )
        for f in parsed_diff.files
    ]
    changed_files_dict = [f.model_dump() for f in changed_files_summary]

    return {
        "changed_files": changed_files_dict,
        "changed_files_summary": changed_files_summary,
        "compressed_diff": parsed_diff.compressed_text,
    }


def code_verifier_node(state: PRVerificationState) -> dict[str, Any]:
    """Node 4: Stage 2 Strict Code Verifier (LLM Call 1).

    Hybrid retrieval: each requirement also queries the repository code
    index (when a DB session and indexed chunks exist) so baseline code
    outside the diff informs the verdict. Retrieval failures degrade to
    diff-only verification — they never fail the run.
    """
    provider = get_ai_provider()
    reqs = state["requirements"]
    changed_files = state["changed_files"]
    compressed_diff = state["compressed_diff"]
    repo_context = _build_repo_context(state)

    verdicts = _run_stage2_verification(
        provider, reqs, changed_files, compressed_diff, repo_context
    )
    return {"verdicts": verdicts, "repo_context": repo_context}


def _build_repo_context(state: PRVerificationState, *, top_k: int = 2) -> str:
    """Collect top-k code chunks per requirement; '' when unavailable."""
    db = state.get("db")
    if db is None:
        return ""
    reqs = state.get("requirements") or []
    if not reqs:
        return ""
    try:
        from app.api.services.repo_index_service import (
            format_code_context,
            retrieve_code_context,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Repository index service unavailable: %s", exc)
        return ""

    project_id = state.get("project_id", "")
    seen: set[tuple[str, int, int]] = set()
    collected = []
    try:
        for req in reqs:
            query = f"{req.get('title', '')}\n{req.get('description', '')}".strip()
            if not query:
                continue
            for item in retrieve_code_context(
                db, project_id=project_id, query_text=query, top_k=top_k
            ):
                key = (item.path, item.start_line, item.end_line)
                if key not in seen:
                    seen.add(key)
                    collected.append(item)
        collected.sort(key=lambda item: item.score, reverse=True)
        return format_code_context(collected[:6])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Repository context retrieval failed, continuing diff-only: %s", exc)
        return ""


def risk_analyst_node(state: PRVerificationState) -> dict[str, Any]:
    """Node 5: Stage 3 Risk, Security & Trust Analyst (LLM Call 2)."""
    provider = get_ai_provider()
    verdicts = state["verdicts"]
    changed_files = state["changed_files"]

    score, trust_level, summary_text, risk_alerts = _run_stage3_risk_analysis(
        provider, verdicts, changed_files
    )

    return {
        "coverage_score": score,
        "trust_level": trust_level,
        "summary_text": summary_text,
        "risk_alerts": risk_alerts,
    }


def persist_and_cache_node(state: PRVerificationState) -> dict[str, Any]:
    """Build, persist, and cache the PR Trust Brief.

    Persistence is best-effort: pasted diffs pin to an ad-hoc pull-request
    snapshot so verdicts and evidence survive across sessions. A failed
    audit-trail write never fails verification — the cached brief is still
    returned.
    """
    project_id = state.get("project_id", "local-project")

    score = state["coverage_score"]
    trust_level = state["trust_level"]
    summary_text = state["summary_text"]
    risk_alerts = state["risk_alerts"]
    verdicts = state["verdicts"]
    changed_files_summary = state["changed_files_summary"]
    reqs = state["requirements"]
    spec_hash = state["spec_hash"]
    diff_hash = state["diff_hash"]

    covered_count = sum(1 for v in verdicts if v.status == "covered")
    partial_count = sum(1 for v in verdicts if v.status == "partial")
    missing_count = sum(1 for v in verdicts if v.status == "missing")

    brief_id = "run-" + hashlib.sha256(
        f"{project_id}:{spec_hash}:{diff_hash}".encode()
    ).hexdigest()[:20]
    now_iso = datetime.now(UTC).isoformat()
    brief = PRTrustBrief(
        id=brief_id,
        projectId=project_id,
        title=f"PR Trust Brief ({trust_level.upper()} Trust)",
        coverageScore=score,
        trustLevel=trust_level,  # type: ignore[arg-type]
        summary=summary_text,
        totalRequirements=len(reqs),
        coveredCount=covered_count,
        partialCount=partial_count,
        missingCount=missing_count,
        verdicts=verdicts,
        riskAlerts=risk_alerts,
        changedFilesSummary=changed_files_summary,
        createdAt=now_iso,
    )

    # Cache for 24 hours
    cache_audit(spec_hash, diff_hash, brief.model_dump(), ttl_seconds=86400)

    # Persist the audit trail (best-effort; never fails verification).
    db = state.get("db")
    if db is not None:
        try:
            from app.api.services.pr_trust_service import persist_verification_run

            run_id = persist_verification_run(
                db,
                project_id=project_id,
                user_id=state.get("user_id", ""),
                brief=brief,
                requirements=reqs,
                diff_hash=diff_hash,
                pr_url=state.get("pr_url"),
            )
            if run_id is not None:
                brief.id = run_id
                cache_audit(spec_hash, diff_hash, brief.model_dump(), ttl_seconds=86400)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Verification persistence skipped: %s", exc)

    logger.info(
        "LangGraph Node [persist_and_cache]: Verification complete for project_id=%s (Score=%d%%, Trust=%s)",
        project_id,
        score,
        trust_level,
    )

    return {"final_brief": brief}


# ---------------------------------------------------------------------------
# Routing Logic & Graph Builder
# ---------------------------------------------------------------------------


def route_cache_decision(state: PRVerificationState) -> str:
    """Conditional Edge: Route to END if cached, else proceed to extract_spec."""
    if state.get("cache_hit"):
        return END
    return "extract_spec"


def build_pr_verification_graph():
    """Build and compile the stateful LangGraph PR Verification workflow."""
    workflow = StateGraph(PRVerificationState)

    # Register Nodes
    workflow.add_node("check_cache", check_cache_node)
    workflow.add_node("extract_spec", extract_spec_node)
    workflow.add_node("clean_diff", clean_diff_node)
    workflow.add_node("code_verifier", code_verifier_node)
    workflow.add_node("risk_analyst", risk_analyst_node)
    workflow.add_node("persist_and_cache", persist_and_cache_node)

    # Register Edges
    workflow.add_edge(START, "check_cache")
    workflow.add_conditional_edges(
        "check_cache",
        route_cache_decision,
        {
            END: END,
            "extract_spec": "extract_spec",
        },
    )
    workflow.add_edge("extract_spec", "clean_diff")
    workflow.add_edge("clean_diff", "code_verifier")
    workflow.add_edge("code_verifier", "risk_analyst")
    workflow.add_edge("risk_analyst", "persist_and_cache")
    workflow.add_edge("persist_and_cache", END)

    return workflow.compile()


# Singleton compiled graph
_COMPILED_GRAPH = None


def get_pr_verification_graph():
    """Lazy singleton getter for compiled graph."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_pr_verification_graph()
    return _COMPILED_GRAPH


def run_pr_verification_workflow(
    *,
    project_id: str,
    user_id: str,
    spec_text: str = "",
    raw_diff: str = "",
    pr_url: str | None = None,
    requirements: list[dict[str, Any]] | None = None,
    db: Session | None = None,
) -> tuple[PRTrustBrief, bool]:
    """Execute the compiled LangGraph PR verification workflow.

    Returns:
      (PRTrustBrief, is_cache_hit)
    """
    graph = get_pr_verification_graph()

    initial_state: PRVerificationState = {
        "project_id": project_id,
        "user_id": user_id,
        "spec_text": spec_text,
        "raw_diff": raw_diff,
        "pr_url": pr_url,
        "requirements": requirements or [],
        "db": db,
    }

    result = graph.invoke(initial_state)
    brief = result.get("final_brief")
    cache_hit = bool(result.get("cache_hit", False))

    if brief is None:
        raise LLMServiceError("LangGraph execution finished without producing a PRTrustBrief.")

    return brief, cache_hit
