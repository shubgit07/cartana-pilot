// Stub requirement extractor.
//
// Heuristic-only: scans chunks for sentences that read like project
// requirements (contain "must", "should", "required", "needs to", "has to",
// "shall") and produces one Requirement per match.
//
// Quality is mediocre by design — the point is that the *pipeline* works
// end-to-end without an LLM configured. When the user wires a real LLM via
// `LLM_PROVIDER`, the same shape is produced but with real reasoning.

import { ExtractedRequirement } from "../AIProvider";

const REQUIREMENT_KEYWORDS = [
  /\bmust\b/i,
  /\bshall\b/i,
  /\bshould\b/i,
  /\bneeds to\b/i,
  /\bhas to\b/i,
  /\bis required\b/i,
  /\bare required\b/i,
  /\brequired to\b/i,
];

interface AIExtractRequirementsInput {
  sourceFilename: string;
  chunks: { id: string; position: number; text: string }[];
}

export function extractRequirementsStub(input: AIExtractRequirementsInput): ExtractedRequirement[] {
  const out: ExtractedRequirement[] = [];
  const seen = new Set<string>();

  for (const chunk of input.chunks) {
    const sentences = splitSentences(chunk.text);
    for (const sentence of sentences) {
      if (!looksLikeRequirement(sentence)) continue;
      const title = makeTitle(sentence);
      if (!title || seen.has(title.toLowerCase())) continue;
      seen.add(title.toLowerCase());
      out.push({
        title,
        description: sentence.trim(),
        chunkIds: [chunk.id],
      });
    }
  }

  // Cap at a reasonable count so we don't blow up the UI on huge inputs.
  return out.slice(0, 40);
}

function splitSentences(text: string): string[] {
  return text
    .replace(/\n+/g, " ")
    .split(/(?<=[.!?])\s+(?=[A-Z])/g)
    .map((s) => s.trim())
    .filter((s) => s.length >= 12);
}

function looksLikeRequirement(sentence: string): boolean {
  if (sentence.length > 320) return false; // skip long paragraphs
  return REQUIREMENT_KEYWORDS.some((re) => re.test(sentence));
}

function makeTitle(sentence: string): string {
  // Take the first clause, cap at ~120 chars.
  const cleaned = sentence.replace(/\s+/g, " ").trim();
  const m = cleaned.match(/^.{1,120}/);
  let title = m ? m[0] : cleaned;
  if (!title.endsWith(".") && title.length === 120) title += "…";
  return title;
}