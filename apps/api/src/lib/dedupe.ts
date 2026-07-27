// Deterministic dedupe key helper — sha256(sourceId + normalized title).
// Used for idempotent re-extraction in Phase 2.

import { createHash } from "crypto";

export function dedupeKey(sourceId: string, title: string): string {
  const norm = title.trim().toLowerCase().replace(/\s+/g, " ");
  return createHash("sha256").update(`${sourceId}|${norm}`).digest("hex");
}