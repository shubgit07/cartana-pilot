// API bootstrap. Starts the HTTP server and the worker process in the
// same process when invoked directly (useful for first-run demos).
// In production you typically run `npm run dev:worker` in a separate
// terminal so the worker can scale independently.

import { createApp } from "./server";
import { config } from "./config";
import { logger } from "./lib/logger";
import { startWorkers } from "./workers";

async function main() {
  const app = createApp();
  app.listen(config.API_PORT, () => {
    logger.info(`API listening on http://localhost:${config.API_PORT}`);
  });

  // Run workers in-process unless we are explicitly a "web only" run.
  if (process.env.CARTANA_WORKER_MODE !== "false") {
    startWorkers();
  }
}

main().catch((err) => {
  logger.error("fatal startup error", { err: String(err) });
  process.exit(1);
});