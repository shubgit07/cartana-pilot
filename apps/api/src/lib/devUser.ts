// Dev user middleware. Phase 1 has no login — we attach a stable dev user
// to every request. Real auth will replace this in a later phase.

import { NextFunction, Request, Response } from "express";
import { prisma } from "../db/prisma";
import { config } from "../config";
import { logger } from "../lib/logger";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      user?: { id: string; email: string | null; name: string | null };
    }
  }
}

let devUserCache: { id: string; email: string | null; name: string | null } | null = null;

export async function getOrCreateDevUser() {
  if (devUserCache) return devUserCache;
  const user = await prisma.user.upsert({
    where: { id: config.DEV_USER_ID },
    update: {},
    create: {
      id: config.DEV_USER_ID,
      email: config.DEV_USER_EMAIL,
      name: config.DEV_USER_NAME,
    },
  });
  devUserCache = { id: user.id, email: user.email, name: user.name };
  logger.info(`Dev user ready: ${user.id}`);
  return devUserCache;
}

export async function devUserMiddleware(req: Request, _res: Response, next: NextFunction) {
  try {
    req.user = await getOrCreateDevUser();
    next();
  } catch (err) {
    next(err);
  }
}