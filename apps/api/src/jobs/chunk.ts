// Chunk job — splits source text into Chunk rows (no embeddings yet).

import { Job } from "bullmq";
import { prisma } from "../db/prisma";
import { chunkText } from "../modules/sources/chunking";
import { sourceEmbedQueue, SourceChunkJobData } from "../queue/queues";
import { logger } from "../lib/logger";

export async function processChunk(job: Job<SourceChunkJobData>) {
  const { sourceId, projectId, userId, text } = job.data;
  logger.info("chunk:start", { sourceId });

  const source = await prisma.source.findFirst({ where: { id: sourceId, userId } });
  if (!source) throw new Error(`Source ${sourceId} not found`);

  try {
    // Idempotent re-run: drop any existing chunks for this source first.
    // (User edits live on Requirement/Task rows, not chunks — this is safe.)
    await prisma.chunk.deleteMany({ where: { sourceId } });

    const pieces = chunkText(text);
    if (pieces.length === 0) {
      throw new Error("Chunker produced 0 pieces from extracted text");
    }

    const created = await prisma.$transaction(
      pieces.map((p) =>
        prisma.chunk.create({
          data: { sourceId, position: p.position, text: p.text },
        })
      )
    );

    await sourceEmbedQueue.add(
      "embed",
      { sourceId, projectId, userId, chunkIds: created.map((c) => c.id) },
      { jobId: `embed-${sourceId}` }
    );

    logger.info("chunk:done", { sourceId, chunks: created.length });
  } catch (err) {
    logger.error("chunk:failed", { sourceId, err: String(err) });
    await prisma.source.update({
      where: { id: sourceId },
      data: { status: "failed", errorMessage: String(err) },
    });
    throw err;
  }
}