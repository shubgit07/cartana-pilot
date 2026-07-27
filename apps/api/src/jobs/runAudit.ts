// Audit job processor — runs the coverage audit engine.

import type { Job } from "bullmq";
import { runAudit } from "../modules/audit/service";
import { logger } from "../lib/logger";
import type { RunAuditJobData } from "../queue/queues";

export async function processRunAudit(job: Job<RunAuditJobData>): Promise<string> {
  const { projectId, userId } = job.data;
  logger.info({ jobId: job.id, projectId }, "Audit job: starting");

  const runId = await runAudit(userId, projectId);

  logger.info({ jobId: job.id, projectId, runId }, "Audit job: complete");
  return runId;
}
