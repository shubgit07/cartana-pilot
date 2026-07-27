// Project routes. Thin — they validate input, call the service, return DTOs.

import { Router } from "express";
import {
  CreateProjectSchema,
  UpdateProjectSchema,
} from "@cartana/shared";
import { requireUser } from "../../lib/requireUser";
import * as projectService from "./service";
import { ValidationError } from "../../lib/errors";

export const projectsRouter: Router = Router();

projectsRouter.get("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projects = await projectService.listProjects(user.id);
    res.json({ projects });
  } catch (err) {
    next(err);
  }
});

projectsRouter.post("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const parsed = CreateProjectSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid project payload", parsed.error.flatten().fieldErrors);
    const project = await projectService.createProject(user.id, parsed.data);
    res.status(201).json({ project });
  } catch (err) {
    next(err);
  }
});

projectsRouter.get("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const id = String(req.params.id ?? "");
    const project = await projectService.getProject(user.id, id);
    res.json({ project });
  } catch (err) {
    next(err);
  }
});

projectsRouter.patch("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const id = String(req.params.id ?? "");
    const parsed = UpdateProjectSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid project payload", parsed.error.flatten().fieldErrors);
    const project = await projectService.updateProject(user.id, id, parsed.data);
    res.json({ project });
  } catch (err) {
    next(err);
  }
});

projectsRouter.delete("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const id = String(req.params.id ?? "");
    await projectService.deleteProject(user.id, id);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});