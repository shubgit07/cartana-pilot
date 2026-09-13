// Shared types used by web + api. Mirrors Prisma enums.

export type SourceStatus = "uploaded" | "processing" | "processed" | "failed";
export type SourceKind = "pdf" | "text";
export type SourceStage = "uploading" | "chunking" | "ready" | "failed";

export type RequirementOrigin = "ai" | "user";
export type RequirementState = "suggested" | "accepted" | "rejected" | "edited";

// ---- API contract types ----

export interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  sourceCount: number;
}

export interface ProjectDetail extends ProjectSummary {
  sources: SourceSummary[];
}

export interface SourceSummary {
  id: string;
  projectId: string;
  filename: string;
  kind: SourceKind;
  status: SourceStatus;
  errorMessage: string | null;
  createdAt: string;
  chunkCount: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: ChatCitation[];
  createdAt: string;
}

export interface ChatCitation {
  sourceId: string;
  filename: string;
  chunkId: string;
  snippet: string;
  score: number;
}

export interface ChatResponse {
  message: ChatMessage;
}

export interface JobStatusView {
  sourceId: string;
  status: SourceStatus;
  stage: SourceStage;
  chunksTotal: number;
  embedded: number;
  errorMessage: string | null;
}

// ---- Requirements ----

export interface RequirementSummary {
  id: string;
  projectId: string;
  title: string;
  description: string | null;
  origin: RequirementOrigin;
  state: RequirementState;
  sourceLinks: { sourceId: string; filename: string }[];
  createdAt: string;
  updatedAt: string;
}

export interface RequirementDetail extends RequirementSummary {
  chunkLinks: { chunkId: string; sourceId: string; filename: string; snippet: string }[];
}

// ---- Phase 4: Decomposed PR Trust Brief & Diff Verification ----

export type VerificationVerdictStatus = "covered" | "partial" | "missing" | "unclear";
export type VerificationConfidence = "high" | "medium" | "low";
export type RiskAlertKind =
  | "missing_backend_check"
  | "no_tests"
  | "scope_creep"
  | "security_gap"
  | "error_handling";
export type RiskAlertSeverity = "critical" | "warning" | "info";
export type PRTrustLevel = "high" | "medium" | "low";

export interface RequirementVerificationVerdict {
  reqId: string;
  title: string;
  status: VerificationVerdictStatus;
  confidence: VerificationConfidence;
  evidenceFile?: string | null;
  evidenceSnippet?: string | null;
  rationale: string;
}

export interface PRRiskAlert {
  kind: RiskAlertKind;
  severity: RiskAlertSeverity;
  title: string;
  description: string;
  affectedFiles?: string[];
}

export interface ChangedFileSummary {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
}

export interface PRTrustBrief {
  id: string;
  projectId: string;
  title: string;
  coverageScore: number;
  trustLevel: PRTrustLevel;
  summary: string;
  totalRequirements: number;
  coveredCount: number;
  partialCount: number;
  missingCount: number;
  verdicts: RequirementVerificationVerdict[];
  riskAlerts: PRRiskAlert[];
  changedFilesSummary: ChangedFileSummary[];
  createdAt: string;
}

export interface VerifyPRInput {
  specText?: string;
  rawDiff?: string;
  githubPrUrl?: string;
}

// ---- Phase 5: Repository index + persisted verification runs ----

export interface RepositoryFileStatus {
  path: string;
  language: string | null;
  lineCount: number | null;
  sizeBytes: number;
  chunksCount: number;
}

export interface RepositoryStatus {
  connected: boolean;
  repoUrl: string | null;
  commitSha: string | null;
  refName: string | null;
  indexedFilesCount: number;
  codeChunksCount: number;
  embeddingDim: number;
  status: string;
  files: RepositoryFileStatus[];
}

export interface RepositoryConnectResult {
  connectionId: string;
  repoUrl: string;
  displayName: string;
  defaultBranch: string;
  commitSha: string;
  filesIndexed: number;
  chunksCreated: number;
  skipped: string[];
  upToDate: boolean;
}

export interface GitHubPullItem {
  number: number;
  title: string;
  headSha: string;
  baseBranch: string;
  updatedAt: string | null;
  url: string;
  author: string | null;
}

export interface GitHubCommitItem {
  sha: string;
  message: string;
  author: string | null;
  date: string | null;
  url: string;
}

export interface RepositorySyncResult {
  snapshotId: string;
  commitSha: string;
  filesIndexed: number;
  chunksCreated: number;
  skipped: string[];
  embeddingModel: string;
  embeddingDim: number;
}

export interface VerificationRunSummary {
  id: string;
  title: string;
  commitSha: string;
  coverageScore: number;
  trustLevel: PRTrustLevel;
  totalRequirements: number;
  coveredCount: number;
  missingCount: number;
  createdAt: string;
}