// Task routes — CRUD + state transitions + relink.

import { Router } from "express";
import { CreateTaskSchema, UpdateTaskSchema } from "@cartana/shared";
import { requireUser } from "../../lib/requireUser";
import * as taskService from "./service";
import { ValidationError } from "../../lib/errors";

export const tasksRouter: Router = Router({ mergeParams: true });

tasksRouter.get("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const tasks = await taskService.listTasks(user.id, projectId);
    res.json({ tasks });
  } catch (err) {
    next(err);
  }
});

tasksRouter.post("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const parsed = CreateTaskSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid task payload", parsed.error.flatten().fieldErrors);
    const task = await taskService.createTask(user.id, projectId, parsed.data);
    res.status(201).json({ task });
  } catch (err) {
    next(err);
  }
});

tasksRouter.get("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const id = String(req.params.id ?? "");
    const task = await taskService.getTask(user.id, projectId, id);
    res.json({ task });
  } catch (err) {
    next(err);
  }
});

tasksRouter.patch("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const id = String(req.params.id ?? "");
    const parsed = UpdateTaskSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid task payload", parsed.error.flatten().fieldErrors);
    const task = await taskService.updateTask(user.id, projectId, id, parsed.data);
    res.json({ task });
  } catch (err) {
    next(err);
  }
});

tasksRouter.delete("/:id", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const id = String(req.params.id ?? "");
    await taskService.deleteTask(user.id, projectId, id);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});