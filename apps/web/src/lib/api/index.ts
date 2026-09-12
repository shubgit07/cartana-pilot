// Single `api` surface — barrels per-resource clients. Components should
// import the named group they need (e.g. `projectsApi`), not this object.

import { auditApi } from "./audit";
import { chatApi } from "./chat";
import { projectsApi } from "./projects";
import { repositoryApi } from "./repository";
import { requirementsApi } from "./requirements";
import { sourcesApi } from "./sources";

export const api = {
  projects: projectsApi,
  sources: sourcesApi,
  chat: chatApi,
  requirements: requirementsApi,
  audit: auditApi,
  repository: repositoryApi,
} as const;

export type Api = typeof api;

export { ApiError, apiClient } from "./client";
export { auditApi } from "./audit";
export { chatApi } from "./chat";
export { projectsApi } from "./projects";
export { repositoryApi } from "./repository";
export { requirementsApi } from "./requirements";
export { sourcesApi } from "./sources";
