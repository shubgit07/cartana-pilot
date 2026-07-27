// Ingest job — loads the file from storage, extracts text, marks source
// as 'processing', then enqueues the chunk job.

import { Job } from "bullmq";
import { prisma } from "../db/prisma";
import { getStorage } from "../storage/StorageProvider";
import { extractText } from "../modules/sources/extractText";
import { sourceChunkQueue, SourceIngestJobData } from "../queue/queues";
import { logger } from "../lib/logger";

export async function processIngest(job: Job<SourceIngestJobData>) {
  const { sourceId, projectId, userId } = job.data;
  logger.info("ingest:start", { sourceId });

  const source = await prisma.source.findFirst({ where: { id: sourceId, userId } });
  if (!source) throw new Error(`Source ${sourceId} not found`);

  await prisma.source.update({
    where: { id: sourceId },
    data: { status: "processing", errorMessage: null },
  });

  try {
    const storage = getStorage();
    const buffer = await storage.get(source.storageKey);
    const text = await extractText(buffer, source.kind);

    if (!text || text.trim().length === 0) {
      throw new Error("No extractable text found in source");
    }

    // Hand the extracted text off to the chunk job via the queue payload.
    // (For very large sources we'd swap this for a side-table staging —
    // BullMQ payloads should stay small.)
    await sourceChunkQueue.add(
      "chunk",
      { sourceId, projectId, userId, text },
      { jobId: `chunk-${sourceId}` }
    );
    logger.info("ingest:done", { sourceId, textLen: text.length });
  } catch (err) {
    logger.error("ingest:failed", { sourceId, err: String(err) });
    await prisma.source.update({
      where: { id: sourceId },
      data: { status: "failed", errorMessage: String(err) },
    });
    throw err;
  }
}