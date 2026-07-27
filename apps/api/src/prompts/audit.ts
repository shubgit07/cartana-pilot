// Coverage audit prompts — separated from business logic per plan §4.
//
// The prompt asks the LLM to judge whether candidate tasks cover a requirement.
// Returns structured JSON so we can parse it into CoverageJudgment[].

import type { AIAuditCoverageInput, AIRiskSummaryInput } from "../ai/AIProvider";

export function buildCoveragePrompt(input: AIAuditCoverageInput): {
  systemPrompt: string;
  userPrompt: string;
} {
  const systemPrompt = [
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
  ].join("\n");

  const taskList = input.candidateTasks.length
    ? input.candidateTasks
        .map(
          (t, i) =>
            `Task ${i + 1}: ${t.title}${t.description ? `\n  Description: ${t.description}` : ""}`
        )
        .join("\n\n")
    : "(No candidate tasks found)";

  const userPrompt = [
    "REQUIREMENT:",
    `Title: ${input.requirement.title}`,
    input.requirement.description
      ? `Description: ${input.requirement.description}`
      : "(No description)",
    "",
    "CANDIDATE TASKS:",
    taskList,
    "",
    "Judge the coverage of each candidate task against the requirement.",
  ].join("\n");

  return { systemPrompt, userPrompt };
}

export function buildRiskSummaryPrompt(input: AIRiskSummaryInput): string {
  const reqLines = input.requirements
    .map((r) => `  - [${r.status}] ${r.title}`)
    .join("\n");

  const findingLines = input.findings
    .map((f) => `  - [${f.severity}] ${f.kind}: ${f.message}`)
    .join("\n");

  return [
    "You are auditing a project for requirement coverage risks.",
    "Based on the coverage status and findings below, write a concise risk summary (3-5 sentences).",
    "Highlight the most critical gaps and what the user should prioritize.",
    "",
    "REQUIREMENT COVERAGE STATUS:",
    reqLines || "  (none)",
    "",
    "AUDIT FINDINGS:",
    findingLines || "  (none)",
  ].join("\n");
}
