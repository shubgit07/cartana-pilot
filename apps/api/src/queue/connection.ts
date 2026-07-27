// Redis connection used by BullMQ.

import IORedis from "ioredis";
import { config } from "../config";

export function createRedisConnection(): IORedis {
  return new IORedis(config.REDIS_URL, {
    maxRetriesPerRequest: null, // BullMQ requires this to be null
  });
}