import type { TaskSummary } from "@cartana/shared";
import { apiClient } from "./client";

export const tasksApi = {
  list: (projectId: string) =>
    apiClient
      .request<{ tasks: TaskSummary[] }>(`/projects/${projectId}/tasks`)
      .then((r) => r.tasks),
  create: (
    projectId: string,
    input: { title: string; description?: string | null; requirementId?: string | null }
  ) =>
    apiClient
      .request<{ task: TaskSummary }>(`/projects/${projectId}/tasks`, {
        method: "POST",
        body: JSON.stringify(input),
      })
      .then((r) => r.task),
  update: (
    projectId: string,
    id: string,
    input: {
      title?: string;
      description?: string | null;
      state?: string;
      requirementId?: string | null;
    }
  ) =>
    apiClient
      .request<{ task: TaskSummary }>(`/projects/${projectId}/tasks/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      })
      .then((r) => r.task),
  remove: (projectId: string, id: string) =>
    apiClient.request<void>(`/projects/${projectId}/tasks/${id}`, { method: "DELETE" }),
};
