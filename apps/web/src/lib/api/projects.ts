import type { ProjectDetail, ProjectSummary } from "@cartana/shared";
import { apiClient } from "./client";

export const projectsApi = {
  list: () =>
    apiClient.request<{ projects: ProjectSummary[] }>("/projects").then((r) => r.projects),
  create: (input: { name: string; description?: string | null }) =>
    apiClient
      .request<{ project: ProjectSummary }>("/projects", {
        method: "POST",
        body: JSON.stringify(input),
      })
      .then((r) => r.project),
  get: (id: string) =>
    apiClient.request<{ project: ProjectDetail }>(`/projects/${id}`).then((r) => r.project),
  remove: (id: string) => apiClient.request<void>(`/projects/${id}`, { method: "DELETE" }),
};
