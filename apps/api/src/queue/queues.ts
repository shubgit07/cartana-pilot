// BullMQ queue definitions. One queue per pipeline stage so they can be
// scaled independently.

import { Queue } from "bullmq";
import { createRedisConnection } from "./connection";
import { QUEUE_NAMES } from "@cartana/shared";

const connection = createRedisConnection();

export const sourceIngestQueue = new Queue(QUEUE_NAMES.sourceIngest, {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: "exponential", delay: 2000 },
    removeOnComplete: { count: 1000 },
    removeOnFail: { count: 1000 },
  },
});

export const sourceChunkQueue = new Queue(QUEUE_NAMES.sourceChunk, {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: "exponential", delay: 2000 },
    removeOnComplete: { count: 1000 },
    removeOnFail: { count: 1000 },
  },
});

export const sourceEmbedQueue = new Queue(QUEUE_NAMES.sourceEmbed, {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: "exponential", delay: 2000 },
    removeOnComplete: { count: 1000 },
    removeOnFail: { count: 1000 },
  },
});

export const extractRequirementsQueue = new Queue(QUEUE_NAMES.extractRequirements, {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: "exponential", delay: 2000 },
    removeOnComplete: { count: 1000 },
    removeOnFail: { count: 1000 },
  },
});

export const extractTasksQueue = new Queue(QUEUE_NAMES.extractTasks, {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: "exponential", delay: 2000 },
    removeOnComplete: { count: 1000 },
    removeOnFail: { count: 1000 },
  },
});

export const runAuditQueue = new Queue(QUEUE_NAMES.runAudit, {
  connection,
  defaultJobOptions: {
    attempts: 1,
    backoff: { type: "exponential", delay: 5000 },
    removeOnComplete: { count: 100 },
    removeOnFail: { count: 100 },
  },
});

export type SourceIngestJobData = {
  sourceId: string;
  projectId: string;
  userId: string;
};

export type SourceChunkJobData = {
  sourceId: string;
  projectId: string;
  userId: string;
  /** Extracted text payload — passed ingest -> chunk to avoid re-reading storage. */
  text?: string;
};

export type SourceEmbedJobData = {
  sourceId: string;
  projectId: string;
  userId: string;
  chunkIds: string[];
};

export type ExtractRequirementsJobData = {
  sourceId: string;
  projectId: string;
  userId: string;
};

export type ExtractTasksJobData = {
  sourceId: string;
  projectId: string;
  userId: string;
};

export type RunAuditJobData = {
  sourceId: string;
  projectId: string;
  userId: string;
};