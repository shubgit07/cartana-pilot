// Extract-tasks job — runs after extractRequirements. Suggests tasks derived
// from chunks, best-effort linking to requirements in the same source pass.

import { Job } from "bullmq";
import { prisma } from "../db/prisma";
import { getAIProvider } from "../ai/AIProvider";
import { ExtractTasksJobData } from "../queue/queues";
import {
  staleOutAITasks,
  upsertTaskFromExtraction,
} from "../modules/tasks/service";
import { logger } from "../lib/logger";

export async function processExtractTasks(job: Job<ExtractTasksJobData>) {
  const { sourceId, projectId, userId } = job.data;
  logger.info("extract-tasks:start", { sourceId });

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
      logger.warn("extract-tasks: no chunks, skipping", { sourceId });
      return;
    }

    // Build a title -> id map for requirements on this source so the
    // extractor can resolve `linkedRequirementTitle` -> id.
    const requirementsForSource = await prisma.requirement.findMany({
      where: {
        projectId,
        userId,
        chunks: { some: { chunk: { sourceId } } },
      },
      select: { id: true, title: true },
    });
    const requirementIdByTitle = new Map<string, string>();
    const requirementPayload = requirementsForSource.map((r) => ({
      title: r.title,
      description: "", // extractor only needs titles + descriptions for context; not id.
    }));
    for (const r of requirementsForSource) {
      requirementIdByTitle.set(r.title.toLowerCase().trim(), r.id);
    }

    const ai = getAIProvider();
    const extracted = await ai.extractTasks({
      sourceFilename: source.filename,
      chunks,
      requirements: requirementPayload,
    });

    const freshKeys = new Set<string>();

    for (const item of extracted) {
      const validChunkIds = item.chunkIds.filter((id) => chunks.some((c) => c.id === id));
      if (validChunkIds.length === 0) validChunkIds.push(chunks[0]!.id);

      const created = await upsertTaskFromExtraction({
        userId,
        projectId,
        item: {
          sourceId,
          title: item.title,
          description: item.description,
          chunkIds: validChunkIds,
          linkedRequirementTitle: item.linkedRequirementTitle,
        },
        requirementIdByTitle,
      });
      if (created.dedupeKey) freshKeys.add(created.dedupeKey);
    }

    const staled = await staleOutAITasks({ userId, projectId, sourceId, freshKeys });
    logger.info("extract-tasks:done", {
      sourceId,
      extracted: extracted.length,
      staled,
    });
  } catch (err) {
    logger.error("extract-tasks:failed", { sourceId, err: String(err) });
    throw err;
  }
}