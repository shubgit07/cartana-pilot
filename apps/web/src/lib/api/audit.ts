import { apiClient } from "./client";

export const auditApi = {
  verifyPR: (
    projectId: string,
    input: import("@cartana/shared").VerifyPRInput
  ) =>
    apiClient.request<{
      brief: import("@cartana/shared").PRTrustBrief;
      fromCache: boolean;
    }>(`/projects/${projectId}/audit/verify-pr`, {
      method: "POST",
      body: JSON.stringify(input),
    }),

  listRuns: (projectId: string) =>
    apiClient.request<{ runs: import("@cartana/shared").VerificationRunSummary[] }>(
      `/projects/${projectId}/audit/runs`
    ),

  getRun: (projectId: string, runId: string) =>
    apiClient.request<import("@cartana/shared").PRTrustBrief>(
      `/projects/${projectId}/audit/runs/${runId}`
    ),
};
