// Source routes — multipart upload + text-paste upload + listing/deletion.
// Thin: validate, call service, return DTOs.

import { Router, Request, Response, NextFunction } from "express";
import multer from "multer";
import {
  CreateSourceFromTextSchema,
} from "@cartana/shared";
import { requireUser } from "../../lib/requireUser";
import * as sourceService from "./service";
import { getSourceJobStatus } from "./service";
import { ValidationError } from "../../lib/errors";

// In-memory upload (dev). For large files swap in multer's diskStorage or a streaming parser.
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 25 * 1024 * 1024 }, // 25MB
});

export const sourcesRouter: Router = Router({ mergeParams: true });

// GET /projects/:projectId/sources
sourcesRouter.get("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const sources = await sourceService.listSources(user.id, projectId);
    res.json({ sources });
  } catch (err) {
    next(err);
  }
});

// POST /projects/:projectId/sources  (multipart, single file)
sourcesRouter.post("/", upload.single("file"), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    if (!req.file) throw new ValidationError("No file uploaded under field 'file'");
    const source = await sourceService.createSourceFromFile({
      userId: user.id,
      projectId,
      filename: req.file.originalname || "upload.bin",
      mimeType: req.file.mimetype || undefined,
      data: req.file.buffer,
    });
    res.status(201).json({ source });
  } catch (err) {
    next(err);
  }
});

// POST /projects/:projectId/sources/text  (paste raw text)
sourcesRouter.post("/text", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const parsed = CreateSourceFromTextSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid payload", parsed.error.flatten().fieldErrors);
    const source = await sourceService.createSourceFromText({
      userId: user.id,
      projectId,
      filename: parsed.data.filename,
      content: parsed.data.content,
    });
    res.status(201).json({ source });
  } catch (err) {
    next(err);
  }
});

// GET /projects/:projectId/sources/:sourceId
sourcesRouter.get("/:sourceId", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const sourceId = String(req.params.sourceId ?? "");
    const source = await sourceService.getSource(user.id, sourceId);
    if (source.projectId !== projectId) throw new ValidationError("Source does not belong to this project");
    res.json({ source });
  } catch (err) {
    next(err);
  }
});

// GET /projects/:projectId/sources/:sourceId/status
sourcesRouter.get("/:sourceId/status", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = requireUser(req);
    const sourceId = String(req.params.sourceId ?? "");
    const status = await getSourceJobStatus(user.id, sourceId);
    res.json({ status });
  } catch (err) {
    next(err);
  }
});

// DELETE /projects/:projectId/sources/:sourceId
sourcesRouter.delete("/:sourceId", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = requireUser(req);
    const sourceId = String(req.params.sourceId ?? "");
    await sourceService.deleteSource(user.id, sourceId);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});