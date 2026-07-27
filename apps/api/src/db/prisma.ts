// Prisma client singleton. Avoids exhausting connections in dev with hot-reload.

import { PrismaClient } from "@prisma/client";
import { logger } from "../lib/logger";

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["warn", "error"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}

logger.debug("Prisma client initialized");