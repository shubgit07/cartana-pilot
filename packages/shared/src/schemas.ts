import { z } from "zod";

// ---- Project ----

export const CreateProjectSchema = z.object({
  name: z.string().min(1).max(120),
  description: z.string().max(2000).optional().nullable(),
});
export type CreateProjectInput = z.infer<typeof CreateProjectSchema>;

export const UpdateProjectSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  description: z.string().max(2000).optional().nullable(),
});
export type UpdateProjectInput = z.infer<typeof UpdateProjectSchema>;

// ---- Source ----

export const CreateSourceFromTextSchema = z.object({
  filename: z.string().min(1).max(255),
  content: z.string().min(1),
});
export type CreateSourceFromTextInput = z.infer<typeof CreateSourceFromTextSchema>;

// Multipart upload is handled by multer in the api - no zod schema here.

// ---- Chat ----

export const ChatAskSchema = z.object({
  question: z.string().min(1).max(4000),
  history: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().min(1).max(8000),
      })
    )
    .max(40)
    .optional(),
});
export type ChatAskInput = z.infer<typeof ChatAskSchema>;

// ---- Phase 2: Requirement + Task ----

export const UpdateRequirementSchema = z.object({
  title: z.string().min(1).max(240).optional(),
  description: z.string().max(4000).nullable().optional(),
  state: z.enum(["suggested", "accepted", "rejected", "edited"]).optional(),
});
export type UpdateRequirementInput = z.infer<typeof UpdateRequirementSchema>;

export const CreateTaskSchema = z.object({
  title: z.string().min(1).max(240),
  description: z.string().max(4000).optional().nullable(),
  requirementId: z.string().nullable().optional(),
});
export type CreateTaskInput = z.infer<typeof CreateTaskSchema>;

export const UpdateTaskSchema = z.object({
  title: z.string().min(1).max(240).optional(),
  description: z.string().max(4000).nullable().optional(),
  state: z.enum(["suggested", "accepted", "rejected", "edited"]).optional(),
  requirementId: z.string().nullable().optional(),
});
export type UpdateTaskInput = z.infer<typeof UpdateTaskSchema>;

// ---- Phase 3: Coverage + Audit ----

export const UpdateCoverageLinkSchema = z.object({
  status: z.enum(["covered", "partial", "unclear", "missing"]).optional(),
  rationale: z.string().max(2000).nullable().optional(),
});
export type UpdateCoverageLinkInput = z.infer<typeof UpdateCoverageLinkSchema>;

// ---- Phase 4: PR Verification & Trust Brief Schemas ----

export const VerifyPRInputSchema = z.object({
  specText: z.string().max(50000).optional(),
  rawDiff: z.string().max(200000).optional(),
  githubPrUrl: z.string().url().max(1000).optional(),
});
export type VerifyPRInputDTO = z.infer<typeof VerifyPRInputSchema>;

export const RequirementVerificationVerdictSchema = z.object({
  reqId: z.string(),
  title: z.string(),
  status: z.enum(["covered", "partial", "missing", "unclear"]),
  confidence: z.enum(["high", "medium", "low"]),
  evidenceFile: z.string().nullable().optional(),
  evidenceSnippet: z.string().nullable().optional(),
  rationale: z.string(),
});

export const PRRiskAlertSchema = z.object({
  kind: z.enum([
    "missing_backend_check",
    "no_tests",
    "scope_creep",
    "security_gap",
    "error_handling",
  ]),
  severity: z.enum(["critical", "warning", "info"]),
  title: z.string(),
  description: z.string(),
  affectedFiles: z.array(z.string()).optional(),
});

export const ChangedFileSummarySchema = z.object({
  filename: z.string(),
  status: z.string(),
  additions: z.number(),
  deletions: z.number(),
});

export const PRTrustBriefSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  title: z.string(),
  coverageScore: z.number().min(0).max(100),
  trustLevel: z.enum(["high", "medium", "low"]),
  summary: z.string(),
  totalRequirements: z.number(),
  coveredCount: z.number(),
  partialCount: z.number(),
  missingCount: z.number(),
  verdicts: z.array(RequirementVerificationVerdictSchema),
  riskAlerts: z.array(PRRiskAlertSchema),
  changedFilesSummary: z.array(ChangedFileSummarySchema),
  createdAt: z.string(),
});