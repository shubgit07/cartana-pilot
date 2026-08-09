"""Decomposed prompts for PR verification (Stage 2) and Risk & Trust analysis (Stage 3).

Designed for compact token footprints so that free-tier LLMs (Cerebras, Groq, Gemini)
can execute quickly without hitting output token limits or hallucinating code evidence.
"""
from __future__ import annotations

import json
from typing import Any


def build_pr_verification_prompt(
    requirements: list[dict[str, Any]],
    changed_files: list[dict[str, Any]],
    diff_hunks: str,
) -> tuple[str, str]:
    """Stage 2 Prompt: Strict Code Verification (LLM Call 1).

    Matches each requirement strictly against code diff hunks and extracts
    concrete evidence snippets (file path + 2-5 line code snippet).
    """
    system_prompt = (
        "You are an expert code verification engine. Your sole job is to cross-reference "
        "a list of feature requirements against git diff code changes.\n\n"
        "Rules:\n"
        "1. For EVERY requirement, judge whether it is 'covered', 'partial', 'missing', or 'unclear' in the diff.\n"
        "2. If 'covered' or 'partial', you MUST provide the exact file path ('evidenceFile') and a 2-5 line code snippet ('evidenceSnippet') from the diff proving it.\n"
        "3. If 'missing', set 'evidenceFile' and 'evidenceSnippet' to null, and explain in 'rationale' what was expected but absent.\n"
        "4. Be strict and objective: UI-only code without backend logic for a requirement is 'partial', not 'covered'.\n"
        "5. Test files alone are NOT evidence of a feature being implemented. If a requirement is only referenced or "
        "exercised by tests (test_*.py) and no implementation of that feature appears in the diff, verdict is 'missing' "
        "even if the tests would pass once the implementation exists.\n"
        "6. Output MUST be valid JSON only matching the schema:\n"
        "{\n"
        '  "verdicts": [\n'
        '    {\n'
        '      "reqId": "R1",\n'
        '      "title": "Requirement title",\n'
        '      "status": "covered" | "partial" | "missing" | "unclear",\n'
        '      "confidence": "high" | "medium" | "low",\n'
        '      "evidenceFile": "path/to/file.ts",\n'
        '      "evidenceSnippet": "code snippet here",\n'
        '      "rationale": "Concise 1-sentence explanation of why it is covered/missing."\n'
        '    }\n'
        "  ]\n"
        "}"
    )

    reqs_formatted = []
    for i, r in enumerate(requirements, start=1):
        req_id = r.get("id") or f"R{i}"
        title = r.get("title", "")
        desc = r.get("description", "")
        reqs_formatted.append(f"[{req_id}] {title}\nDescription: {desc}")

    files_list = "\n".join(
        f"- {f.get('filename')} (+{f.get('additions', 0)} / -{f.get('deletions', 0)})"
        for f in changed_files
    )

    user_prompt = (
        f"### Feature Requirements:\n{chr(10).join(reqs_formatted)}\n\n"
        f"### Changed Files:\n{files_list}\n\n"
        f"### Git Diff Hunks:\n```diff\n{diff_hunks}\n```\n\n"
        "Evaluate every single requirement against the diff and return the JSON object."
    )

    return system_prompt, user_prompt


def build_pr_risk_summary_prompt(
    verdicts: list[dict[str, Any]],
    changed_files_summary: list[dict[str, Any]],
) -> tuple[str, str]:
    """Stage 3 Prompt: Risk, Security & Trust Level Analysis (LLM Call 2).

    Consumes compact verdicts (~300 tokens) + file list to synthesize
    security gaps, test coverage flags, scope creep, and compute Trust Score.
    """
    system_prompt = (
        "You are a Principal Software Engineer and Security Lead evaluating the safety "
        "and completeness of a Pull Request before merging.\n\n"
        "You are given the requirement verification verdicts and the list of changed files.\n"
        "Evaluate:\n"
        "1. Security & Backend Gaps: Did the PR implement frontend UI but omit backend auth, validation, or rate limits?\n"
        "2. Test Coverage: Were test files modified/added to verify the new features?\n"
        "3. Scope Creep: Were unrelated files, dependencies, or configs altered outside the requirements?\n"
        "4. Calculate Trust Level ('high', 'medium', 'low') and Coverage Score (0-100%):\n"
        "   - 'high': >=80% requirements covered, tests present, zero critical security gaps.\n"
        "   - 'medium': 50-79% covered, or minor omissions.\n"
        "   - 'low': <50% covered, or critical missing backend/security checks.\n\n"
        "Output MUST be valid JSON only matching the schema:\n"
        "{\n"
        '  "coverageScore": 80,\n'
        '  "trustLevel": "high" | "medium" | "low",\n'
        '  "summary": "2-3 sentence executive brief of PR readiness and trust score.",\n'
        '  "riskAlerts": [\n'
        '    {\n'
        '      "kind": "missing_backend_check" | "no_tests" | "scope_creep" | "security_gap" | "error_handling",\n'
        '      "severity": "critical" | "warning" | "info",\n'
        '      "title": "Short alert title",\n'
        '      "description": "Clear explanation of the risk and recommended fix.",\n'
        '      "affectedFiles": ["path/to/file.py"]\n'
        '    }\n'
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"### Verification Verdicts:\n{json.dumps(verdicts, indent=2)}\n\n"
        f"### Changed Files Summary:\n{json.dumps(changed_files_summary, indent=2)}\n\n"
        "Perform the risk and trust analysis and return the JSON object."
    )

    return system_prompt, user_prompt
