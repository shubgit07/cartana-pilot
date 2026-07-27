// Small helper to pull the dev user off the request and fail loud if missing.
// (Defense-in-depth: in Phase 1 we always have one, but this guards against
// misconfigured middleware.)

import { Request } from "express";
import { UnauthorizedError } from "./errors";

export function requireUser(req: Request) {
  if (!req.user) throw new UnauthorizedError("No user context on request");
  return req.user;
}