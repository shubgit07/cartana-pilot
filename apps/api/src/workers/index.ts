// Worker entry point — runs BullMQ workers for the Phase 1 queues.

import { Worker } from "bullmq";
import { createRedisConnection } from "../queue/connection";
import { QUEUE_NAMES } from "@cartana/shared";
import { processIngest } from "../jobs/ingest";
import { processChunk } from "../jobs/chunk";
import { processEmbed } from "../jobs/embed";
import { processExtractRequirements } from "../jobs/extractRequirements";
import { processExtractTasks } from "../jobs/extractTasks";
import { processRunAudit } from "../jobs/runAudit";
import { logger } from "../lib/logger";

const connection = createRedisConnection();

export function startWorkers() {
  const ingestWorker = new Worker(QUEUE_NAMES.sourceIngest, processIngest as any, { connection });
  const chunkWorker = new Worker(QUEUE_NAMES.sourceChunk, processChunk as any, { connection });
  const embedWorker = new Worker(QUEUE_NAMES.sourceEmbed, processEmbed as any, { connection });
  const extractReqsWorker = new Worker(
    QUEUE_NAMES.extractRequirements,
    processExtractRequirements as any,
    { connection }
  );
  const extractTasksWorker = new Worker(
    QUEUE_NAMES.extractTasks,
    processExtractTasks as any,
    { connection }
  );
  const runAuditWorker = new Worker(QUEUE_NAMES.runAudit, processRunAudit as any, { connection });

  for (const w of [ingestWorker, chunkWorker, embedWorker, extractReqsWorker, extractTasksWorker, runAuditWorker]) {
    w.on("completed", (job) => logger.info(`job completed: ${w.name}/${job.id}`));
    w.on("failed", (job, err) =>
      logger.error(`job failed: ${w.name}/${job?.id}`, { err: String(err) })
    );
    w.on("error", (err) => logger.error(`worker error: ${w.name}`, { err: String(err) }));
  }

  const shutdown = async (signal: string) => {
    logger.info(`worker shutting down (${signal})`);
    await Promise.all([
      ingestWorker.close(),
      chunkWorker.close(),
      embedWorker.close(),
      extractReqsWorker.close(),
      extractTasksWorker.close(),
      runAuditWorker.close(),
    ]);
    process.exit(0);
  };
  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));

  logger.info("workers started");
}

if (require.main === module) {
  startWorkers();
}