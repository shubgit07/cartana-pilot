// Centralized constants shared by api + web. Keep these stable - schema/dep changes.

/**
 * Vector dimension for the configured embedding model.
 * Cloudflare Workers AI @cf/baai/bge-base-en-v1.5 -> 768.
 * Changing the embedding model later = a re-embed migration (NOT a free swap).
 */
export const EMBEDDING_DIM = 768 as const;

/**
 * Implicit dev user for the single-user local MVP.
 * Phase 1 has no login. Real auth is a later phase.
 */
export const DEV_USER_ID = "dev-user" as const;

/**
 * Phase 1 queue names. Keep stable - workers and producers both reference these.
 */
export const QUEUE_NAMES = {
  sourceIngest: "source-ingest",
  sourceChunk: "source-chunk",
  sourceEmbed: "source-embed",
  extractRequirements: "extract-requirements",
  extractTasks: "extract-tasks",
  runAudit: "run-audit",
} as const;

export type QueueName = (typeof QUEUE_NAMES)[keyof typeof QUEUE_NAMES];