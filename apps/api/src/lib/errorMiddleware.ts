// Centralized error handler. Maps AppError -> proper HTTP status codes.
// Anything else is 500 (logged, not leaked).

import { ErrorRequestHandler, RequestHandler } from "express";
import { AppError } from "./errors";
import { logger } from "./logger";

export const notFoundHandler: RequestHandler = (req, res) => {
  res.status(404).json({
    error: { code: "not_found", message: `Route not found: ${req.method} ${req.originalUrl}` },
  });
};

export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  if (err instanceof AppError) {
    res.status(err.status).json({
      error: { code: err.code, message: err.message, details: err.details ?? undefined },
    });
    return;
  }
  logger.error("unhandled error", { err: String(err), stack: (err as Error)?.stack });
  res.status(500).json({
    error: { code: "internal_error", message: "Internal server error" },
  });
};