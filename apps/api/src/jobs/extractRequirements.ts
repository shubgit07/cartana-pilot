// Extract-requirements job — runs after embed completes.
// Idempotent: re-running on the same source preserves user edits and
// marks superseded AI suggestions as rejected instead of duplicating.

import { Job } from "bullmq";
import { prisma } from "../db/prisma";
import { getAIProvider } from "../ai/AIProvider";
import { ExtractRequirementsJobData, extractTasksQueue } from "../queue/queues";
import {
  staleOutAIRequirements,
  upsertRequirementFromExtraction,
} from "../modules/requirements/service";
import { logger } from "../lib/logger";

export async function processExtractRequirements(job: Job<ExtractRequirementsJobData>) {
  const { sourceId, projectId, userId } = job.data;
  logger.info("extract-reqs:start", { sourceId });

  try {
    const source = await prisma.source.findFirst({
      where: { id: sourceId, userId },
    });
    if (!source) throw new Error(`Source ${sourceId} not found`);

    const chunks = await prisma.chunk.findMany({
      where: { sourceId },
      orderBy: { position: "asc" },
      select: { id: true, position: true, text: true },
    });
    if (chunks.length === 0) {
      logger.warn("extract-reqs: no chunks, skipping", { sourceId });
      return;
    }

    const ai = getAIProvider();
    const extracted = await ai.extractRequirements({
      sourceFilename: source.filename,
      chunks,
    });

    // Track which dedupe keys we saw in this run (for stale-out).
    const freshKeys = new Set<string>();

    for (const item of extracted) {
      // Filter to chunkIds that belong to this source.
      const validChunkIds = item.chunkIds.filter((id) => chunks.some((c) => c.id === id));
      if (validChunkIds.length === 0) {
        // Fall back to the first chunk if the AI didn't provide any.
        validChunkIds.push(chunks[0]!.id);
      }
      const created = await upsertRequirementFromExtraction({
        userId,
        projectId,
        item: {
          sourceId,
          title: item.title,
          description: item.description,
          chunkIds: validChunkIds,
        },
      });
      if (created.dedupeKey) freshKeys.add(created.dedupeKey);
    }

    const staled = await staleOutAIRequirements({ userId, projectId, sourceId, freshKeys });
    logger.info("extract-reqs:done", {
      sourceId,
      extracted: extracted.length,
      staled,
    });

    // Hand off to the task extractor (Phase 2B).
    await extractTasksQueue.add(
      "extract-tasks",
      { sourceId, projectId, userId },
      { jobId: `extract-tasks-${sourceId}` }
    );
  } catch (err) {
    logger.error("extract-reqs:failed", { sourceId, err: String(err) });
    throw err;
  }
}