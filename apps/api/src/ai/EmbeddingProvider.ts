// EmbeddingProvider — interface every implementation must satisfy.
// NEVER call a provider SDK directly outside this file.

import { config } from "../config";
import { logger } from "../lib/logger";
import { EMBEDDING_DIM } from "@cartana/shared";

export interface EmbeddingProvider {
  /** Human-readable id for logging. */
  readonly id: string;
  /** The configured vector dimension. Must equal EMBEDDING_DIM. */
  readonly dim: number;
  /** Embed a list of texts. Returns L2-normalized vectors. */
  embed(texts: string[]): Promise<number[][]>;
}

// -------------------------------------------------------------------------
// Stub provider — deterministic pseudo-embeddings so the pipeline never
// crashes in dev. Quality is poor (lexical hash projected into vector
// space) — only useful for exercising the full flow without real creds.
// -------------------------------------------------------------------------

class StubEmbeddingProvider implements EmbeddingProvider {
  readonly id = "stub";
  readonly dim = EMBEDDING_DIM;

  async embed(texts: string[]): Promise<number[][]> {
    return texts.map((t) => hashToVector(t, this.dim));
  }
}

function hashToVector(text: string, dim: number): number[] {
  const v = new Array<number>(dim).fill(0);
  const tokens = text.toLowerCase().split(/\W+/).filter(Boolean);
  for (const tok of tokens) {
    let h = 2166136261;
    for (let i = 0; i < tok.length; i++) {
      h ^= tok.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    const idx = Math.abs(h) % dim;
    v[idx] = (v[idx] ?? 0) + 1;
  }
  // L2 normalize
  let norm = 0;
  for (const x of v) norm += x * x;
  norm = Math.sqrt(norm) || 1;
  for (let i = 0; i < v.length; i++) v[i] = (v[i] ?? 0) / norm;
  return v;
}

// -------------------------------------------------------------------------
// Cloudflare Workers AI provider — DECIDED target.
// POSTs to /accounts/{id}/ai/run/{model}. Uses fetch so no extra SDK dep.
// -------------------------------------------------------------------------

class CloudflareEmbeddingProvider implements EmbeddingProvider {
  readonly id = "cloudflare";
  readonly dim = EMBEDDING_DIM;
  private readonly url: string;
  private readonly headers: Record<string, string>;

  constructor(accountId: string, apiToken: string, model: string) {
    this.url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/run/${model}`;
    this.headers = {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": "application/json",
    };
  }

  async embed(texts: string[]): Promise<number[][]> {
    const results: number[][] = [];
    // Cloudflare's AI run endpoint accepts a single `text` per request in
    // many model configs; batch as parallel requests.
    const responses = await Promise.all(
      texts.map(async (text) => {
        const res = await fetch(this.url, {
          method: "POST",
          headers: this.headers,
          body: JSON.stringify({ text }),
        });
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Cloudflare embed failed: ${res.status} ${body}`);
        }
        const json = (await res.json()) as { result?: { data?: number[][] } | number[] };
        // Accept either { data: [[...]] } (Workers AI batched shape) or a flat array.
        if (json.result && Array.isArray((json.result as { data?: number[][] }).data)) {
          return ((json.result as { data: number[][] }).data[0] ?? []) as number[];
        }
        if (json.result && Array.isArray(json.result)) {
          return json.result as number[];
        }
        throw new Error("Cloudflare embed: unexpected response shape");
      })
    );
    for (const vec of responses) {
      if (vec.length !== this.dim) {
        throw new Error(`Embedding dim mismatch: got ${vec.length}, expected ${this.dim}`);
      }
      results.push(l2normalize(vec));
    }
    return results;
  }
}

function l2normalize(v: number[]): number[] {
  let n = 0;
  for (const x of v) n += x * x;
  n = Math.sqrt(n) || 1;
  return v.map((x) => x / n);
}

// -------------------------------------------------------------------------
// Factory + caching
// -------------------------------------------------------------------------

let cached: EmbeddingProvider | null = null;

export function getEmbeddingProvider(): EmbeddingProvider {
  if (cached) return cached;
  switch (config.EMBEDDING_PROVIDER) {
    case "cloudflare": {
      if (!config.CLOUDFLARE_ACCOUNT_ID || !config.CLOUDFLARE_API_TOKEN) {
        logger.warn(
          "EMBEDDING_PROVIDER=cloudflare but credentials missing. Falling back to stub embeddings."
        );
        cached = new StubEmbeddingProvider();
        return cached;
      }
      cached = new CloudflareEmbeddingProvider(
        config.CLOUDFLARE_ACCOUNT_ID,
        config.CLOUDFLARE_API_TOKEN,
        config.EMBEDDING_MODEL
      );
      return cached;
    }
    case "stub":
    default:
      cached = new StubEmbeddingProvider();
      return cached;
  }
}

/**
 * Format a vector for pgvector's literal input: '[v1,v2,...]'.
 */
export function toPgVectorLiteral(v: number[]): string {
  return `[${v.join(",")}]`;
}