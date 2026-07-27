// Requirement routes — thin: validate, call service, return DTOs.

import { Router } from "express";
import { UpdateRequirementSchema } from "@cartana/shared";
import { requireUser } from "../../lib/requireUser";
import * as reqService from "./service";
import { ValidationError } from "../../lib/errors";

export const requirementsRouter: Router = Router({ mergeParams: true });

requirementsRouter.get("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const requirements = await reqService.listRequirements(user.id, projectId);
    res.json({ requirements });
  } catch (err) {
    next(err);
  }
});

requirementsRouter.get("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const id = String(req.params.id ?? "");
    const requirement = await reqService.getRequirement(user.id, projectId, id);
    res.json({ requirement });
  } catch (err) {
    next(err);
  }
});

requirementsRouter.patch("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const id = String(req.params.id ?? "");
    const parsed = UpdateRequirementSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid requirement payload", parsed.error.flatten().fieldErrors);
    const requirement = await reqService.updateRequirement(user.id, projectId, id, parsed.data);
    res.json({ requirement });
  } catch (err) {
    next(err);
  }
});

requirementsRouter.delete("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const id = String(req.params.id ?? "");
    await reqService.deleteRequirement(user.id, projectId, id);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});