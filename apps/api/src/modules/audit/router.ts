// Audit routes — thin: validate, call service, return DTOs.

import { Router } from "express";
import { UpdateCoverageLinkSchema } from "@cartana/shared";
import { requireUser } from "../../lib/requireUser";
import * as auditService from "./service";
import { ValidationError, NotFoundError } from "../../lib/errors";
import { runAuditQueue } from "../../queue/queues";

export const auditRouter: Router = Router({ mergeParams: true });

// Trigger a new audit run (enqueues a BullMQ job)
auditRouter.post("/run", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");

    // Enqueue the audit job
    const job = await runAuditQueue.add("run-audit", {
      sourceId: "",
      projectId,
      userId: user.id,
    });

    res.json({ jobId: job.id, status: "queued" });
  } catch (err) {
    next(err);
  }
});

// List past audit runs
auditRouter.get("/runs", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const runs = await auditService.listAuditRuns(user.id, projectId);
    res.json({ runs });
  } catch (err) {
    next(err);
  }
});

// Get the latest audit run (with findings + coverage links)
auditRouter.get("/latest", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const run = await auditService.getLatestAudit(user.id, projectId);
    if (!run) {
      res.status(404).json({ error: { code: "not_found", message: "No audit run found" } });
      return;
    }
    res.json({ run });
  } catch (err) {
    next(err);
  }
});

// Check job status (polled by the frontend after POST /run)
auditRouter.get("/run/:jobId/status", async (req, res, next) => {
  try {
    const jobId = String(req.params.jobId ?? "");
    const job = await runAuditQueue.getJob(jobId);
    if (!job) throw new NotFoundError("Job not found");
    const state = await job.getState();
    const result = job.returnvalue;
    res.json({ jobId, state, result });
  } catch (err) {
    next(err);
  }
});

// ---- Coverage links ----

export const coverageRouter: Router = Router({ mergeParams: true });

coverageRouter.get("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const links = await auditService.listCoverageLinks(user.id, projectId);
    res.json({ coverageLinks: links });
  } catch (err) {
    next(err);
  }
});

coverageRouter.patch("/:linkId", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const linkId = String(req.params.linkId ?? "");
    const parsed = UpdateCoverageLinkSchema.safeParse(req.body);
    if (!parsed.success)
      throw new ValidationError("Invalid coverage link payload", parsed.error.flatten().fieldErrors);
    const updated = await auditService.updateCoverageLink(
      user.id,
      projectId,
      linkId,
      parsed.data
    );
    res.json({ coverageLink: updated });
  } catch (err) {
    next(err);
  }
});
