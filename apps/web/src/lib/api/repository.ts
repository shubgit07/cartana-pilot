import { apiClient } from "./client";

export const repositoryApi = {
  getStatus: (projectId: string) =>
    apiClient.request<import("@cartana/shared").RepositoryStatus>(
      `/projects/${projectId}/repository/status`
    ),

  sync: (
    projectId: string,
    input: { files: { path: string; content: string }[] }
  ) =>
    apiClient.request<import("@cartana/shared").RepositorySyncResult>(
      `/projects/${projectId}/repository/sync`,
      { method: "POST", body: JSON.stringify(input) }
    ),
};
