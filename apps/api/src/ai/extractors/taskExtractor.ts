// Stub task extractor.
//
// Heuristic-only: scans chunks for sentences that begin with action verbs
// (build, create, implement, design, develop, add, test, deploy, set up,
// configure, prepare, generate, write, document) and produces one Task per
// match. When possible, links the task to the requirement whose title
// shares the most tokens with the task sentence.

import { ExtractedTask } from "../AIProvider";

const ACTION_VERBS = [
  "build",
  "create",
  "implement",
  "design",
  "develop",
  "add",
  "test",
  "deploy",
  "set up",
  "setup",
  "configure",
  "prepare",
  "generate",
  "write",
  "document",
  "integrate",
  "publish",
  "submit",
  "review",
];

interface AIExtractTasksInput {
  sourceFilename: string;
  chunks: { id: string; position: number; text: string }[];
  requirements: { title: string; description: string }[];
}

export function extractTasksStub(input: AIExtractTasksInput): ExtractedTask[] {
  const out: ExtractedTask[] = [];
  const seen = new Set<string>();

  for (const chunk of input.chunks) {
    const sentences = splitSentences(chunk.text);
    for (const sentence of sentences) {
      const action = leadingActionVerb(sentence);
      if (!action) continue;
      const title = makeTitle(sentence, action);
      if (!title || seen.has(title.toLowerCase())) continue;
      seen.add(title.toLowerCase());

      const linked = bestRequirementMatch(title, input.requirements);
      out.push({
        title,
        description: sentence.trim(),
        chunkIds: [chunk.id],
        linkedRequirementTitle: linked ?? undefined,
      });
    }
  }

  return out.slice(0, 60);
}

function splitSentences(text: string): string[] {
  return text
    .replace(/\n+/g, " ")
    .split(/(?<=[.!?])\s+(?=[A-Z])/g)
    .map((s) => s.trim())
    .filter((s) => s.length >= 10);
}

function leadingActionVerb(sentence: string): string | null {
  const lower = sentence.toLowerCase();
  for (const verb of ACTION_VERBS) {
    if (lower.startsWith(verb + " ") || lower.startsWith(verb + ",")) {
      return verb;
    }
  }
  return null;
}

function makeTitle(sentence: string, action: string): string {
  const cleaned = sentence.replace(/\s+/g, " ").trim();
  const rest = cleaned.slice(action.length).replace(/^[,:]\s*/, "");
  const title = (action.charAt(0).toUpperCase() + action.slice(1) + " " + rest).trim();
  return title.length > 160 ? title.slice(0, 160) + "…" : title;
}

function bestRequirementMatch(taskTitle: string, reqs: { title: string; description: string }[]): string | null {
  if (reqs.length === 0) return null;
  const taskTokens = new Set(tokenize(taskTitle));
  let best: { title: string; score: number } | null = null;
  for (const r of reqs) {
    const reqTokens = tokenize(`${r.title} ${r.description ?? ""}`);
    let score = 0;
    for (const t of reqTokens) if (taskTokens.has(t)) score++;
    if (score > 0 && (!best || score > best.score)) {
      best = { title: r.title, score };
    }
  }
  return best ? best.title : null;
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 3);
}