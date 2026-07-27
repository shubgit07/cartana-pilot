// Express app factory. Kept separate from index.ts so workers and tests
// can import the app without binding a port.

import express from "express";
import cors from "cors";
import { config } from "./config";
import { devUserMiddleware } from "./lib/devUser";
import { errorHandler, notFoundHandler } from "./lib/errorMiddleware";
import { projectsRouter } from "./modules/projects/router";
import { sourcesRouter } from "./modules/sources/router";
import { chatRouter } from "./modules/chat/router";
import { requirementsRouter } from "./modules/requirements/router";
import { tasksRouter } from "./modules/tasks/router";
import { auditRouter, coverageRouter } from "./modules/audit/router";
import { logger } from "./lib/logger";

export function createApp() {
  const app = express();

  app.use(
    cors({
      origin: true, // dev: any. In prod, narrow this to the web origin.
      credentials: true,
    })
  );
  app.use(express.json({ limit: "2mb" }));

  // Health
  app.get("/health", (_req, res) => {
    res.json({ ok: true, env: config.NODE_ENV });
  });

  // Auth (dev user) — Phase 1 only.
  app.use(devUserMiddleware);

  // Routes
  app.use("/projects", projectsRouter);
  app.use("/projects/:projectId/sources", sourcesRouter);
  app.use("/projects/:projectId/chat", chatRouter);
  app.use("/projects/:projectId/requirements", requirementsRouter);
  app.use("/projects/:projectId/tasks", tasksRouter);
  app.use("/projects/:projectId/audit", auditRouter);
  app.use("/projects/:projectId/coverage", coverageRouter);

  // 404 + error handler last
  app.use(notFoundHandler);
  app.use(errorHandler);

  logger.info("Express app created");
  return app;
}