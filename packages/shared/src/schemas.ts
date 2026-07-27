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