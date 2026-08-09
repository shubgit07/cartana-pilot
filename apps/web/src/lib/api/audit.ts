import type {
  AuditRunSummary,
  AuditRunDetail,
  CoverageLinkSummary,
} from "@cartana/shared";
import { apiClient } from "./client";

export const auditApi = {
  runAudit: (projectId: string) =>
    apiClient.request<{ jobId: string; status: string }>(
      `/projects/${projectId}/audit/run`,
      { method: "POST" }
    ),

  jobStatus: (projectId: string, jobId: string) =>
    apiClient.request<{ jobId: string; state: string; result?: string }>(
      `/projects/${projectId}/audit/run/${jobId}/status`
    ),

  listRuns: (projectId: string) =>
    apiClient
      .request<{ runs: AuditRunSummary[] }>(`/projects/${projectId}/audit/runs`)
      .then((r) => r.runs),

  getLatest: (projectId: string) =>
    apiClient
      .request<{ run: AuditRunDetail }>(`/projects/${projectId}/audit/latest`)
      .then((r) => r.run),

  listCoverageLinks: (projectId: string) =>
    apiClient
      .request<{ coverageLinks: CoverageLinkSummary[] }>(
        `/projects/${projectId}/coverage`
      )
      .then((r) => r.coverageLinks),

  updateCoverageLink: (
    projectId: string,
    linkId: string,
    input: { status?: string; rationale?: string | null }
  ) =>
    apiClient
      .request<{ coverageLink: CoverageLinkSummary }>(
        `/projects/${projectId}/coverage/${linkId}`,
        { method: "PATCH", body: JSON.stringify(input) }
      )
      .then((r) => r.coverageLink),

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
};
