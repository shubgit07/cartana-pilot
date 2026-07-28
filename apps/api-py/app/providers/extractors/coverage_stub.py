"""Heuristic coverage stub.

Port of ``apps/api/src/ai/extractors/coverageStub.ts``.

Judges coverage based on token overlap between the requirement and each
candidate task. Low quality by design — the point is that the pipeline works
end-to-end without an LLM.
"""
from __future__ import annotations

import re

from app.providers.ai_provider import (
    AIAuditCoverageInput,
    AIAuditCoverageOutput,
    CoverageJudgment,
)


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [t for t in cleaned.split() if len(t) > 3]


def coverage_stub(input: AIAuditCoverageInput) -> AIAuditCoverageOutput:
    if not input.candidateTasks:
        return AIAuditCoverageOutput(judgments=[
            CoverageJudgment(
                status="missing",
                rationale="No candidate tasks were found for this requirement.",
            )
        ])

    req_tokens = _tokenize(
        f"{input.requirement.get('title', '')} {input.requirement.get('description', '')}"
    )
    req_set = set(req_tokens)

    judgments: list[CoverageJudgment] = []
    for task in input.candidateTasks:
        task_tokens = _tokenize(f"{task.get('title', '')} {task.get('description', '')}")
        if not task_tokens:
            judgments.append(CoverageJudgment(
                status="unclear",
                rationale="Task has no meaningful text to compare.",
            ))
            continue

        overlap = sum(1 for t in task_tokens if t in req_set)
        ratio = overlap / max(len(req_tokens), 1)

        if ratio >= 0.4:
            judgments.append(CoverageJudgment(
                status="covered",
                rationale=f"Strong token overlap ({overlap} shared terms) between requirement and task.",
            ))
        elif ratio >= 0.15:
            judgments.append(CoverageJudgment(
                status="partial",
                rationale=f"Moderate token overlap ({overlap} shared terms). Task addresses some aspects.",
            ))
        else:
            judgments.append(CoverageJudgment(
                status="unclear",
                rationale=f"Low token overlap ({overlap} shared terms). Task may not be related.",
            ))

    return AIAuditCoverageOutput(judgments=judgments)
