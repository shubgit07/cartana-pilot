// Heuristic coverage stub — used when no real LLM is configured.
//
// Judges coverage based on token overlap between the requirement and each
// candidate task. Low quality by design — the point is that the pipeline
// works end-to-end without an LLM. When a real LLM is wired via
// `LLM_PROVIDER=fireworks`, the same input shape produces real reasoning.

import type { AIAuditCoverageInput, AIAuditCoverageOutput, CoverageJudgment } from "../AIProvider";

export function coverageStub(input: AIAuditCoverageInput): AIAuditCoverageOutput {
  if (input.candidateTasks.length === 0) {
    return {
      judgments: [
        {
          status: "missing",
          rationale: "No candidate tasks were found for this requirement.",
        },
      ],
    };
  }

  const reqTokens = tokenize(
    `${input.requirement.title} ${input.requirement.description ?? ""}`
  );
  const reqSet = new Set(reqTokens);

  const judgments: CoverageJudgment[] = input.candidateTasks.map((task) => {
    const taskTokens = tokenize(`${task.title} ${task.description ?? ""}`);
    if (taskTokens.length === 0) {
      return {
        status: "unclear",
        rationale: "Task has no meaningful text to compare.",
      };
    }

    let overlap = 0;
    for (const t of taskTokens) {
      if (reqSet.has(t)) overlap++;
    }

    const ratio = overlap / Math.max(reqTokens.length, 1);

    if (ratio >= 0.4) {
      return {
        status: "covered",
        rationale: `Strong token overlap (${overlap} shared terms) between requirement and task.`,
      };
    } else if (ratio >= 0.15) {
      return {
        status: "partial",
        rationale: `Moderate token overlap (${overlap} shared terms). Task addresses some aspects.`,
      };
    } else {
      return {
        status: "unclear",
        rationale: `Low token overlap (${overlap} shared terms). Task may not be related.`,
      };
    }
  });

  return { judgments };
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 3);
}
