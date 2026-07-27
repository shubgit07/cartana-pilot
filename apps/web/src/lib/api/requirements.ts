import type { RequirementSummary } from "@cartana/shared";
import { apiClient } from "./client";

export const requirementsApi = {
  list: (projectId: string) =>
    apiClient
      .request<{ requirements: RequirementSummary[] }>(`/projects/${projectId}/requirements`)
      .then((r) => r.requirements),
  update: (
    projectId: string,
    id: string,
    input: { title?: string; description?: string | null; state?: string }
  ) =>
    apiClient
      .request<{ requirement: RequirementSummary }>(
        `/projects/${projectId}/requirements/${id}`,
        { method: "PATCH", body: JSON.stringify(input) }
      )
      .then((r) => r.requirement),
  remove: (projectId: string, id: string) =>
    apiClient.request<void>(`/projects/${projectId}/requirements/${id}`, { method: "DELETE" }),
};
