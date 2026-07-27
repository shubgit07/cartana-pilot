// Chat routes — single endpoint per project.

import { Router } from "express";
import { ChatAskSchema } from "@cartana/shared";
import { requireUser } from "../../lib/requireUser";
import * as chatService from "./service";
import { ValidationError } from "../../lib/errors";

export const chatRouter: Router = Router({ mergeParams: true });

chatRouter.post("/", async (req, res, next) => {
  try {
    const user = requireUser(req);
    const projectId = String(req.params.projectId ?? "");
    const parsed = ChatAskSchema.safeParse(req.body);
    if (!parsed.success) throw new ValidationError("Invalid chat payload", parsed.error.flatten().fieldErrors);
    const result = await chatService.askProject(user.id, projectId, parsed.data);
    res.json(result);
  } catch (err) {
    next(err);
  }
});