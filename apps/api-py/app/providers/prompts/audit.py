"""Coverage audit prompts.

Port of ``apps/api/src/prompts/audit.ts``. Separated from business logic per
the architecture rules. The prompt asks the LLM to judge whether candidate
tasks cover a requirement, returning structured JSON.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.providers.ai_provider import AIAuditCoverageInput, AIRiskSummaryInput


def build_coverage_prompt(input: AIAuditCoverageInput) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the coverage audit LLM call."""
    system_prompt = "\n".join([
        "You are Cartana's coverage audit engine.",
        "Given a requirement and candidate tasks, judge whether the tasks fully cover the requirement.",
        "For each candidate task, return a judgment with:",
        '  - status: "covered" | "partial" | "unclear" | "missing"',
        "  - rationale: a short explanation (1-2 sentences)",
        "",
        "Status definitions:",
        '- "covered": The task directly and fully implements the requirement.',
        '- "partial": The task addresses some aspects but not all of the requirement.',
        '- "unclear": The task might be related but its scope is ambiguous.',
        '- "missing": No task covers this requirement.',
        "",
        "If there are no candidate tasks, return a single judgment with status 'missing'.",
        "",
        "Return ONLY valid JSON in this format:",
        '{"judgments": [{"status": "covered", "rationale": "..."}, ...]}',
        "The judgments array must have one entry per candidate task, in order.",
    ])

    if input.candidateTasks:
        task_list = "\n\n".join(
            f"Task {i + 1}: {t.get('title', '')}"
            + (f"\n  Description: {t.get('description', '')}" if t.get("description") else "")
            for i, t in enumerate(input.candidateTasks)
        )
    else:
        task_list = "(No candidate tasks found)"

    user_prompt = "\n".join([
        "REQUIREMENT:",
        f"Title: {input.requirement.get('title', '')}",
        f"Description: {input.requirement.get('description') or '(No description)'}",
        "",
        "CANDIDATE TASKS:",
        task_list,
        "",
        "Judge the coverage of each candidate task against the requirement.",
    ])

    return system_prompt, user_prompt


def build_risk_summary_prompt(input: AIRiskSummaryInput) -> str:
    req_lines = "\n".join(
        f"  - [{r.get('status', '?')}] {r.get('title', '')}" for r in input.requirements
    )
    finding_lines = "\n".join(
        f"  - [{f.get('severity', '?')}] {f.get('kind', '')}: {f.get('message', '')}"
        for f in input.findings
    )

    return "\n".join([
        "You are auditing a project for requirement coverage risks.",
        "Based on the coverage status and findings below, write a concise risk summary (3-5 sentences).",
        "Highlight the most critical gaps and what the user should prioritize.",
        "",
        "REQUIREMENT COVERAGE STATUS:",
        req_lines or "  (none)",
        "",
        "AUDIT FINDINGS:",
        finding_lines or "  (none)",
    ])
