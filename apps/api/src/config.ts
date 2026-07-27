// Config — single source of truth for env vars.
// Validated once on boot via zod. If validation fails, we crash loud (no silent stub-everything).

import "dotenv/config";
import { z } from "zod";

const ConfigSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  LOG_LEVEL: z.enum(["fatal", "error", "warn", "info", "debug", "trace"]).default("info"),

  API_PORT: z.coerce.number().int().positive().default(4000),
  API_BASE_URL: z.string().url().default("http://localhost:4000"),

  DATABASE_URL: z.string().min(1),
  REDIS_URL: z.string().min(1).default("redis://localhost:6379"),

  STORAGE_DRIVER: z.enum(["local"]).default("local"),
  STORAGE_LOCAL_ROOT: z.string().min(1).default("./storage"),

  EMBEDDING_PROVIDER: z.enum(["cloudflare", "stub"]).default("stub"),
  EMBEDDING_MODEL: z.string().default("@cf/baai/bge-base-en-v1.5"),

  CLOUDFLARE_ACCOUNT_ID: z.string().optional().default(""),
  CLOUDFLARE_API_TOKEN: z.string().optional().default(""),

  LLM_PROVIDER: z.enum(["stub", "cloudflare", "openai", "anthropic", "fireworks"]).default("stub"),
  LLM_MODEL: z.string().default("stub"),
  OPENAI_API_KEY: z.string().optional().default(""),
  ANTHROPIC_API_KEY: z.string().optional().default(""),
  CLOUDFLARE_LLM_MODEL: z.string().optional().default("@cf/meta/llama-3.1-8b-instruct"),

  FIREWORKS_API_KEY: z.string().optional().default(""),
  FIREWORKS_MODEL: z.string().optional().default("accounts/fireworks/models/llama-v3p1-8b-instruct"),

  DEV_USER_ID: z.string().default("dev-user"),
  DEV_USER_EMAIL: z.string().default("dev@cartana.local"),
  DEV_USER_NAME: z.string().default("Local Dev"),
});

const parsed = ConfigSchema.safeParse(process.env);
if (!parsed.success) {
  // eslint-disable-next-line no-console
  console.error("Invalid environment configuration:");
  // eslint-disable-next-line no-console
  console.error(parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const config = parsed.data;
export type Config = typeof config;