// Shared types used by web + api. Mirrors Prisma enums.

export type SourceStatus = "uploaded" | "processing" | "processed" | "failed";
export type SourceKind = "pdf" | "text";
export type SourceStage = "uploading" | "chunking" | "ready" | "failed";

export type TaskOrigin = "ai" | "user";
export type TaskState = "suggested" | "accepted" | "rejected" | "edited";

export type RequirementOrigin = "ai" | "user";
export type RequirementState = "suggested" | "accepted" | "rejected" | "edited";

export type CoverageStatus = "covered" | "partial" | "unclear" | "missing";
export type CoverageOrigin = "ai-suggested" | "user-confirmed";

export type AuditSeverity = "info" | "warning" | "critical";

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

// ---- Phase 2: Requirement + Task ----

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

export interface TaskSummary {
  id: string;
  projectId: string;
  requirementId: string | null;
  requirementTitle: string | null;
  title: string;
  description: string | null;
  origin: TaskOrigin;
  state: TaskState;
  sourceLinks: { sourceId: string; filename: string }[];
  createdAt: string;
  updatedAt: string;
}

export interface TaskDetail extends TaskSummary {
  chunkLinks: { chunkId: string; sourceId: string; filename: string; snippet: string }[];
}

// ---- Phase 3: Coverage + Audit ----

export type AuditFindingKind =
  | "uncovered_requirement"
  | "partial_coverage"
  | "vague_requirement"
  | "deadline_risk"
  | "orphan_task"
  | "other";

export interface CoverageLinkSummary {
  id: string;
  projectId: string;
  requirementId: string;
  requirementTitle: string;
  taskId: string;
  taskTitle: string;
  status: CoverageStatus;
  origin: CoverageOrigin;
  rationale: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AuditFindingSummary {
  id: string;
  runId: string;
  kind: AuditFindingKind;
  severity: AuditSeverity;
  message: string;
  requirementId: string | null;
  requirementTitle: string | null;
  taskId: string | null;
  taskTitle: string | null;
  createdAt: string;
}

export interface AuditRunSummary {
  id: string;
  projectId: string;
  summary: string | null;
  findingCount: number;
  criticalCount: number;
  warningCount: number;
  infoCount: number;
  createdAt: string;
}

export interface AuditRunDetail extends AuditRunSummary {
  findings: AuditFindingSummary[];
  coverageLinks: CoverageLinkSummary[];
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