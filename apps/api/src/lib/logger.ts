// Lightweight structured logger. Uses pino when available, console fallback otherwise.

import { config } from "../config";

type Level = "debug" | "info" | "warn" | "error";

const levelPriority: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const currentLevel = (config.LOG_LEVEL as Level) ?? "info";

function fmt(level: Level, msg: string, meta?: Record<string, unknown>) {
  const ts = new Date().toISOString();
  const base = `${ts} ${level.toUpperCase()} ${msg}`;
  if (meta && Object.keys(meta).length > 0) {
    return `${base} ${JSON.stringify(meta)}`;
  }
  return base;
}

function shouldLog(level: Level) {
  return levelPriority[level] >= levelPriority[currentLevel];
}

export const logger = {
  debug(msg: string, meta?: Record<string, unknown>) {
    if (shouldLog("debug")) console.log(fmt("debug", msg, meta));
  },
  info(msg: string, meta?: Record<string, unknown>) {
    if (shouldLog("info")) console.log(fmt("info", msg, meta));
  },
  warn(msg: string, meta?: Record<string, unknown>) {
    if (shouldLog("warn")) console.warn(fmt("warn", msg, meta));
  },
  error(msg: string, meta?: Record<string, unknown>) {
    if (shouldLog("error")) console.error(fmt("error", msg, meta));
  },
};

export type Logger = typeof logger;