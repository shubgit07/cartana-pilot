import type { JobStatusView, SourceSummary } from "@cartana/shared";
import { apiClient } from "./client";

export const sourcesApi = {
  list: (projectId: string) =>
    apiClient
      .request<{ sources: SourceSummary[] }>(`/projects/${projectId}/sources`)
      .then((r) => r.sources),
  uploadFile: (projectId: string, file: File): Promise<SourceSummary> => {
    const fd = new FormData();
    fd.append("file", file);
    return apiClient
      .requestForm<{ source: SourceSummary }>(`/projects/${projectId}/sources`, fd)
      .then((r) => r.source);
  },
  createFromText: (projectId: string, filename: string, content: string) =>
    apiClient
      .request<{ source: SourceSummary }>(`/projects/${projectId}/sources/text`, {
        method: "POST",
        body: JSON.stringify({ filename, content }),
      })
      .then((r) => r.source),
  remove: (projectId: string, sourceId: string) =>
    apiClient.request<void>(`/projects/${projectId}/sources/${sourceId}`, { method: "DELETE" }),
  status: (projectId: string, sourceId: string) =>
    apiClient
      .request<{ status: JobStatusView }>(`/projects/${projectId}/sources/${sourceId}/status`)
      .then((r) => r.status),
};
