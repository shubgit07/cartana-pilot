import { apiClient } from "./client";

export const repositoryApi = {
  getStatus: (projectId: string) =>
    apiClient.request<import("@cartana/shared").RepositoryStatus>(
      `/projects/${projectId}/repository/status`
    ),

  connect: (projectId: string, repoUrl: string) =>
    apiClient.request<import("@cartana/shared").RepositoryConnectResult>(
      `/projects/${projectId}/repository/connect`,
      { method: "POST", body: JSON.stringify({ repoUrl }) }
    ),

  resync: (projectId: string) =>
    apiClient.request<import("@cartana/shared").RepositoryConnectResult>(
      `/projects/${projectId}/repository/resync`,
      { method: "POST" }
    ),

  disconnect: (projectId: string) =>
    apiClient.request<void>(`/projects/${projectId}/repository/connection`, {
      method: "DELETE",
    }),

  pulls: (projectId: string, state = "open") =>
    apiClient.request<{ pulls: import("@cartana/shared").GitHubPullItem[] }>(
      `/projects/${projectId}/repository/pulls?state=${state}`
    ),

  commits: (projectId: string, limit = 10) =>
    apiClient.request<{ commits: import("@cartana/shared").GitHubCommitItem[] }>(
      `/projects/${projectId}/repository/commits?limit=${limit}`
    ),
};
