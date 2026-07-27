// AIProvider — generation side. Interface only; provider SDKs go behind it.
//
// Providers: stub | cloudflare | fireworks
// All providers share the same interface so swapping is a one-file change.

import { config } from "../config";
import { logger } from "../lib/logger";
import { ChatCitation } from "@cartana/shared";
import { extractRequirementsStub } from "./extractors/requirementExtractor";
import { extractTasksStub } from "./extractors/taskExtractor";
import { coverageStub } from "./extractors/coverageStub";
import { buildCoveragePrompt, buildRiskSummaryPrompt } from "../prompts/audit";

export interface AIChatInput {
  question: string;
  history?: { role: "user" | "assistant"; content: string }[];
  passages: { chunkId: string; sourceId: string; filename: string; text: string; score: number }[];
}

export interface AIChatOutput {
  answer: string;
  citations: ChatCitation[];
}

// ---- Phase 2: structured extraction ----

export interface ExtractedRequirement {
  title: string;
  description: string;
  chunkIds: string[];
}

export interface ExtractedTask {
  title: string;
  description: string;
  chunkIds: string[];
  linkedRequirementTitle?: string;
}

export interface AIExtractRequirementsInput {
  sourceFilename: string;
  chunks: { id: string; position: number; text: string }[];
}

export interface AIExtractTasksInput {
  sourceFilename: string;
  chunks: { id: string; position: number; text: string }[];
  requirements: { title: string; description: string }[];
}

// ---- Phase 3: coverage audit ----

export interface CoverageJudgment {
  status: "covered" | "partial" | "unclear" | "missing";
  rationale: string;
}

export interface AIAuditCoverageInput {
  requirement: { title: string; description: string };
  candidateTasks: { title: string; description: string }[];
}

export interface AIAuditCoverageOutput {
  judgments: CoverageJudgment[];
}

export interface AIRiskSummaryInput {
  requirements: { title: string; status: string }[];
  findings: { kind: string; severity: string; message: string }[];
}

export interface AIRiskSummaryOutput {
  summary: string;
}

export interface AIProvider {
  readonly id: string;
  chat(input: AIChatInput): Promise<AIChatOutput>;
  extractRequirements(input: AIExtractRequirementsInput): Promise<ExtractedRequirement[]>;
  extractTasks(input: AIExtractTasksInput): Promise<ExtractedTask[]>;
  auditCoverage(input: AIAuditCoverageInput): Promise<AIAuditCoverageOutput>;
  riskSummary(input: AIRiskSummaryInput): Promise<AIRiskSummaryOutput>;
}

// -------------------------------------------------------------------------
// Stub — retrieval-only, heuristic-based. Used when no LLM is configured.
// -------------------------------------------------------------------------

class StubAIProvider implements AIProvider {
  readonly id = "stub";

  async chat(input: AIChatInput): Promise<AIChatOutput> {
    const citations: ChatCitation[] = input.passages.map((p) => ({
      sourceId: p.sourceId,
      filename: p.filename,
      chunkId: p.chunkId,
      snippet: p.text.length > 240 ? `${p.text.slice(0, 240)}…` : p.text,
      score: p.score,
    }));

    const summary = citations
      .slice(0, 3)
      .map((c, i) => `(${i + 1}) ${c.snippet}`)
      .join("\n\n");

    const answer = citations.length
      ? `Based on the uploaded project material, here is what I found that looks relevant to your question:\n\n${summary}\n\n(See citations below. No live LLM is configured yet — answers are retrieval-only.)`
      : `I could not find any passages in the uploaded material that match your question. Try rephrasing, or upload more sources.`;

    return { answer, citations };
  }

  async extractRequirements(input: AIExtractRequirementsInput) {
    return extractRequirementsStub(input);
  }

  async extractTasks(input: AIExtractTasksInput) {
    return extractTasksStub(input);
  }

  async auditCoverage(input: AIAuditCoverageInput): Promise<AIAuditCoverageOutput> {
    return coverageStub(input);
  }

  async riskSummary(input: AIRiskSummaryInput): Promise<AIRiskSummaryOutput> {
    const total = input.requirements.length;
    const covered = input.requirements.filter((r) => r.status === "covered").length;
    const missing = input.requirements.filter((r) => r.status === "missing").length;
    const partial = input.requirements.filter((r) => r.status === "partial").length;
    const critical = input.findings.filter((f) => f.severity === "critical").length;

    const parts: string[] = [];
    parts.push(`Coverage audit complete. ${covered}/${total} requirements are fully covered.`);
    if (partial > 0) parts.push(`${partial} requirement${partial === 1 ? "" : "s"} have partial coverage.`);
    if (missing > 0) parts.push(`${missing} requirement${missing === 1 ? "" : "s"} are not covered by any task.`);
    if (critical > 0) parts.push(`${critical} critical finding${critical === 1 ? "" : "s"} require attention.`);

    return { summary: parts.join(" ") };
  }
}

// -------------------------------------------------------------------------
// Cloudflare generation provider — Workers AI.
// -------------------------------------------------------------------------

class CloudflareAIProvider implements AIProvider {
  readonly id = "cloudflare";
  private readonly url: string;
  private readonly headers: Record<string, string>;
  private readonly model: string;

  constructor(accountId: string, apiToken: string, model: string) {
    this.model = model;
    this.url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/run/${model}`;
    this.headers = {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": "application/json",
    };
  }

  async chat(input: AIChatInput): Promise<AIChatOutput> {
    const sysPrompt = buildSystemPrompt(input);
    const res = await fetch(this.url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        messages: [
          { role: "system", content: sysPrompt },
          ...((input.history ?? []).map((m) => ({ role: m.role, content: m.content })) as {
            role: string;
            content: string;
          }[]),
          { role: "user", content: input.question },
        ],
      }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Cloudflare LLM failed: ${res.status} ${body}`);
    }
    const json = (await res.json()) as { result?: { response?: string } | string };
    const answer =
      typeof json.result === "string"
        ? json.result
        : (json.result && (json.result as { response?: string }).response) || "";

    const citations: ChatCitation[] = input.passages.map((p) => ({
      sourceId: p.sourceId,
      filename: p.filename,
      chunkId: p.chunkId,
      snippet: p.text.length > 240 ? `${p.text.slice(0, 240)}…` : p.text,
      score: p.score,
    }));

    return { answer, citations };
  }

  async extractRequirements(input: AIExtractRequirementsInput): Promise<ExtractedRequirement[]> {
    return extractRequirementsStub(input);
  }

  async extractTasks(input: AIExtractTasksInput): Promise<ExtractedTask[]> {
    return extractTasksStub(input);
  }

  async auditCoverage(input: AIAuditCoverageInput): Promise<AIAuditCoverageOutput> {
    return coverageStub(input);
  }

  async riskSummary(input: AIRiskSummaryInput): Promise<AIRiskSummaryOutput> {
    const total = input.requirements.length;
    const covered = input.requirements.filter((r) => r.status === "covered").length;
    const missing = input.requirements.filter((r) => r.status === "missing").length;
    return {
      summary: `Coverage: ${covered}/${total} fully covered, ${missing} missing. ${input.findings.length} findings.`,
    };
  }
}

// -------------------------------------------------------------------------
// Fireworks AI — OpenAI-compatible chat completions.
// https://api.fireworks.ai/inference/v1/chat/completions
// Supports JSON mode via response_format for structured output.
// -------------------------------------------------------------------------

class FireworksAIProvider implements AIProvider {
  readonly id = "fireworks";
  private readonly url = "https://api.fireworks.ai/inference/v1/chat/completions";
  private readonly headers: Record<string, string>;
  private readonly model: string;

  constructor(apiKey: string, model: string) {
    this.model = model;
    this.headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
  }

  async chat(input: AIChatInput): Promise<AIChatOutput> {
    const sysPrompt = buildSystemPrompt(input);
    const res = await fetch(this.url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: sysPrompt },
          ...((input.history ?? []).map((m) => ({ role: m.role, content: m.content })) as {
            role: string;
            content: string;
          }[]),
          { role: "user", content: input.question },
        ],
        max_tokens: 2048,
        temperature: 0.3,
      }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Fireworks LLM failed: ${res.status} ${body}`);
    }

    const json = (await res.json()) as {
      choices?: { message?: { content?: string } }[];
    };
    const answer = json.choices?.[0]?.message?.content ?? "";

    const citations: ChatCitation[] = input.passages.map((p) => ({
      sourceId: p.sourceId,
      filename: p.filename,
      chunkId: p.chunkId,
      snippet: p.text.length > 240 ? `${p.text.slice(0, 240)}…` : p.text,
      score: p.score,
    }));

    return { answer, citations };
  }

  async extractRequirements(input: AIExtractRequirementsInput): Promise<ExtractedRequirement[]> {
    return extractRequirementsStub(input);
  }

  async extractTasks(input: AIExtractTasksInput): Promise<ExtractedTask[]> {
    return extractTasksStub(input);
  }

  async auditCoverage(input: AIAuditCoverageInput): Promise<AIAuditCoverageOutput> {
    const { systemPrompt, userPrompt } = buildCoveragePrompt(input);

    const res = await fetch(this.url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        response_format: { type: "json_object" },
        max_tokens: 2048,
        temperature: 0.2,
      }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Fireworks audit failed: ${res.status} ${body}`);
    }

    const json = (await res.json()) as {
      choices?: { message?: { content?: string } }[];
    };
    const raw = json.choices?.[0]?.message?.content ?? "{}";

    try {
      const parsed = JSON.parse(raw) as {
        judgments?: { status?: string; rationale?: string }[];
      };
      const judgments: CoverageJudgment[] = (parsed.judgments ?? []).map((j) => ({
        status: normalizeStatus(j.status),
        rationale: j.rationale ?? "",
      }));
      return { judgments };
    } catch {
      logger.warn({ raw }, "Fireworks audit returned invalid JSON — falling back to stub");
      return coverageStub(input);
    }
  }

  async riskSummary(input: AIRiskSummaryInput): Promise<AIRiskSummaryOutput> {
    const prompt = buildRiskSummaryPrompt(input);

    const res = await fetch(this.url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: "You are a project risk analyst. Be concise." },
          { role: "user", content: prompt },
        ],
        max_tokens: 1024,
        temperature: 0.3,
      }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Fireworks risk summary failed: ${res.status} ${body}`);
    }

    const json = (await res.json()) as {
      choices?: { message?: { content?: string } }[];
    };
    const summary = json.choices?.[0]?.message?.content ?? "";
    return { summary };
  }
}

// -------------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------------

function buildSystemPrompt(input: AIChatInput): string {
  const ctx = input.passages
    .slice(0, 8)
    .map((p, i) => `[${i + 1}] (${p.filename}) ${p.text}`)
    .join("\n\n");
  return [
    "You are Cartana, a project specification copilot.",
    "Answer the user's question using ONLY the passages below.",
    "If the answer is not in the passages, say so clearly.",
    "Cite passages inline as [n] and refer to filenames when relevant.",
    "Be concise.",
    "",
    "--- PASSAGES ---",
    ctx,
  ].join("\n");
}

function normalizeStatus(s?: string): CoverageJudgment["status"] {
  switch (s) {
    case "covered":
      return "covered";
    case "partial":
      return "partial";
    case "unclear":
      return "unclear";
    case "missing":
      return "missing";
    default:
      return "unclear";
  }
}

// -------------------------------------------------------------------------
// Factory + caching
// -------------------------------------------------------------------------

let cached: AIProvider | null = null;

export function getAIProvider(): AIProvider {
  if (cached) return cached;
  switch (config.LLM_PROVIDER) {
    case "cloudflare": {
      if (!config.CLOUDFLARE_ACCOUNT_ID || !config.CLOUDFLARE_API_TOKEN) {
        logger.warn("LLM_PROVIDER=cloudflare but credentials missing. Using stub.");
        cached = new StubAIProvider();
        return cached;
      }
      cached = new CloudflareAIProvider(
        config.CLOUDFLARE_ACCOUNT_ID,
        config.CLOUDFLARE_API_TOKEN,
        config.CLOUDFLARE_LLM_MODEL
      );
      return cached;
    }
    case "fireworks": {
      if (!config.FIREWORKS_API_KEY) {
        logger.warn("LLM_PROVIDER=fireworks but FIREWORKS_API_KEY missing. Using stub.");
        cached = new StubAIProvider();
        return cached;
      }
      cached = new FireworksAIProvider(config.FIREWORKS_API_KEY, config.FIREWORKS_MODEL);
      return cached;
    }
    case "stub":
    default:
      cached = new StubAIProvider();
      return cached;
  }
}
