// Embed job — generates embeddings for chunks via EmbeddingProvider and
// stores them in pgvector. Uses a raw SQL UPDATE with the vector literal
// because Prisma doesn't have first-class support for the `vector` type.

import { Job } from "bullmq";
import { prisma } from "../db/prisma";
import { getEmbeddingProvider, toPgVectorLiteral } from "../ai/EmbeddingProvider";
import { SourceEmbedJobData, extractRequirementsQueue } from "../queue/queues";
import { logger } from "../lib/logger";

export async function processEmbed(job: Job<SourceEmbedJobData>) {
  const { sourceId, userId, chunkIds } = job.data;
  logger.info("embed:start", { sourceId, chunks: chunkIds.length });

  const source = await prisma.source.findFirst({ where: { id: sourceId, userId } });
  if (!source) throw new Error(`Source ${sourceId} not found`);

  try {
    const provider = getEmbeddingProvider();

    // Fetch chunk texts
    const chunks = await prisma.chunk.findMany({
      where: { id: { in: chunkIds } },
      select: { id: true, text: true },
    });
    if (chunks.length === 0) return;

    const vectors = await provider.embed(chunks.map((c) => c.text));

    // Write embeddings via raw SQL. The vector column accepts a string
    // literal '[v1,v2,...]'. We use parameterization to avoid injection.
    for (let i = 0; i < chunks.length; i++) {
      const id = chunks[i]!.id;
      const vec = vectors[i]!;
      const lit = toPgVectorLiteral(vec);
      await prisma.$executeRawUnsafe(
        `UPDATE "Chunk" SET embedding = $1::vector WHERE id = $2`,
        lit,
        id
      );
    }

    await prisma.source.update({
      where: { id: sourceId },
      data: { status: "processed", errorMessage: null },
    });
    logger.info("embed:done", { sourceId, embedded: chunks.length });

    // Phase 2: kick off requirement + task extraction. Done as a separate
    // job so embed stays fast and the extraction steps can be retried
    // independently.
    await extractRequirementsQueue.add(
      "extract-reqs",
      { sourceId, projectId, userId },
      { jobId: `extract-reqs-${sourceId}` }
    );
  } catch (err) {
    logger.error("embed:failed", { sourceId, err: String(err) });
    await prisma.source.update({
      where: { id: sourceId },
      data: { status: "failed", errorMessage: String(err) },
    });
    throw err;
  }
}