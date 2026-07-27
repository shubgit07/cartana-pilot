// Single `api` surface — barrels per-resource clients. Components should
// import the named group they need (e.g. `projectsApi`), not this object.

import { auditApi } from "./audit";
import { chatApi } from "./chat";
import { projectsApi } from "./projects";
import { requirementsApi } from "./requirements";
import { sourcesApi } from "./sources";
import { tasksApi } from "./tasks";

export const api = {
  projects: projectsApi,
  sources: sourcesApi,
  chat: chatApi,
  requirements: requirementsApi,
  tasks: tasksApi,
  audit: auditApi,
} as const;

export type Api = typeof api;

export { ApiError, apiClient } from "./client";
export { auditApi } from "./audit";
export { chatApi } from "./chat";
export { projectsApi } from "./projects";
export { requirementsApi } from "./requirements";
export { sourcesApi } from "./sources";
export { tasksApi } from "./tasks";
