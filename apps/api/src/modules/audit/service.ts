// Audit service — the core Phase 3 engine.
//
// Flow:
// 1. Fetch effective requirements (accepted + user-created, not rejected)
// 2. Fetch effective tasks (accepted + user-created, not rejected)
// 3. For each requirement:
//    a. Embed the requirement title+description
//    b. pgvector similarity search against task descriptions → top-5 candidates
//    c. Call AIProvider.auditCoverage() for judgment
//    d. Write/update CoverageLink rows (preserve user-confirmed links)
// 4. Generate AuditFinding rows (uncovered, partial, vague, orphan)
// 5. Generate risk summary via AIProvider
// 6. Create AuditRun with summary + findings

import { prisma } from "../../db/prisma";
import { getAIProvider, type CoverageJudgment } from "../../ai/AIProvider";
import { getEmbeddingProvider } from "../../ai/EmbeddingProvider";
import { logger } from "../../lib/logger";
import { NotFoundError } from "../../lib/errors";
import type {
  AuditFindingSummary,
  AuditRunSummary,
  AuditRunDetail,
  CoverageLinkSummary,
} from "@cartana/shared";

// ---- DTOs ----

function toCoverageLinkSummary(row: {
  id: string;
  projectId: string;
  requirementId: string;
  taskId: string;
  status: string;
  origin: string;
  rationale: string | null;
  createdAt: Date;
  updatedAt: Date;
  requirement: { title: string };
  task: { title: string };
}): CoverageLinkSummary {
  return {
    id: row.id,
    projectId: row.projectId,
    requirementId: row.requirementId,
    requirementTitle: row.requirement.title,
    taskId: row.taskId,
    taskTitle: row.task.title,
    status: row.status as CoverageLinkSummary["status"],
    origin: row.origin as CoverageLinkSummary["origin"],
    rationale: row.rationale,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function toFindingSummary(row: {
  id: string;
  runId: string;
  kind: string;
  severity: string;
  message: string;
  requirementId: string | null;
  taskId: string | null;
  createdAt: Date;
  requirement: { title: string } | null;
  task: { title: string } | null;
}): AuditFindingSummary {
  return {
    id: row.id,
    runId: row.runId,
    kind: row.kind as AuditFindingSummary["kind"],
    severity: row.severity as AuditFindingSummary["severity"],
    message: row.message,
    requirementId: row.requirementId,
    requirementTitle: row.requirement?.title ?? null,
    taskId: row.taskId,
    taskTitle: row.task?.title ?? null,
    createdAt: row.createdAt.toISOString(),
  };
}

function toRunSummary(row: {
  id: string;
  projectId: string;
  summary: string | null;
  createdAt: Date;
  findings: { severity: string }[];
}): AuditRunSummary {
  const findings = row.findings;
  return {
    id: row.id,
    projectId: row.projectId,
    summary: row.summary,
    findingCount: findings.length,
    criticalCount: findings.filter((f) => f.severity === "critical").length,
    warningCount: findings.filter((f) => f.severity === "warning").length,
    infoCount: findings.filter((f) => f.severity === "info").length,
    createdAt: row.createdAt.toISOString(),
  };
}

// ---- Public API ----

export async function listAuditRuns(userId: string, projectId: string): Promise<AuditRunSummary[]> {
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const runs = await prisma.auditRun.findMany({
    where: { projectId, userId },
    orderBy: { createdAt: "desc" },
    include: { findings: { select: { severity: true } } },
  });

  return runs.map(toRunSummary);
}

export async function getLatestAudit(userId: string, projectId: string): Promise<AuditRunDetail | null> {
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const run = await prisma.auditRun.findFirst({
    where: { projectId, userId },
    orderBy: { createdAt: "desc" },
    include: {
      findings: {
        include: {
          requirement: { select: { title: true } },
          task: { select: { title: true } },
        },
        orderBy: [{ severity: "asc" }, { createdAt: "desc" }],
      },
      coverageLinks: {
        include: {
          requirement: { select: { title: true } },
          task: { select: { title: true } },
        },
        orderBy: { requirementId: "asc" },
      },
    },
  });

  if (!run) return null;

  const summary = toRunSummary({
    id: run.id,
    projectId: run.projectId,
    summary: run.summary,
    createdAt: run.createdAt,
    findings: run.findings.map((f) => ({ severity: f.severity })),
  });

  return {
    ...summary,
    findings: run.findings.map(toFindingSummary),
    coverageLinks: run.coverageLinks.map(toCoverageLinkSummary),
  };
}

export async function listCoverageLinks(
  userId: string,
  projectId: string
): Promise<CoverageLinkSummary[]> {
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const links = await prisma.coverageLink.findMany({
    where: { projectId, userId },
    include: {
      requirement: { select: { title: true } },
      task: { select: { title: true } },
    },
    orderBy: [{ requirementId: "asc" }, { status: "asc" }],
  });

  return links.map(toCoverageLinkSummary);
}

export async function updateCoverageLink(
  userId: string,
  projectId: string,
  linkId: string,
  input: { status?: string; rationale?: string | null }
): Promise<CoverageLinkSummary> {
  const link = await prisma.coverageLink.findFirst({
    where: { id: linkId, projectId, userId },
  });
  if (!link) throw new NotFoundError("Coverage link not found");

  const updated = await prisma.coverageLink.update({
    where: { id: linkId },
    data: {
      ...(input.status ? { status: input.status as never } : {}),
      ...(input.rationale !== undefined ? { rationale: input.rationale } : {}),
      origin: "user_confirmed",
    },
    include: {
      requirement: { select: { title: true } },
      task: { select: { title: true } },
    },
  });

  return toCoverageLinkSummary(updated);
}

// ---- Core audit engine (called by the BullMQ job) ----

export async function runAudit(userId: string, projectId: string): Promise<string> {
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const provider = getAIProvider();
  const embeddingProvider = getEmbeddingProvider();

  // 1. Fetch effective requirements
  const requirements = await prisma.requirement.findMany({
    where: {
      projectId,
      userId,
      state: { notIn: ["rejected", "suggested"] },
    },
  });

  // 2. Fetch effective tasks
  const tasks = await prisma.task.findMany({
    where: {
      projectId,
      userId,
      state: { notIn: ["rejected", "suggested"] },
    },
  });

  logger.info(
    { projectId, reqCount: requirements.length, taskCount: tasks.length },
    "Audit: starting coverage analysis"
  );

  // Collect findings + coverage links
  const findingsToCreate: {
    kind: string;
    severity: string;
    message: string;
    requirementId?: string;
    taskId?: string;
  }[] = [];

  const coverageLinksToCreate: {
    requirementId: string;
    taskId: string;
    status: string;
    rationale: string;
  }[] = [];

  const reqCoverageStatus: { title: string; status: string }[] = [];

  for (const req of requirements) {
    // 3a. Embed the requirement
    const reqText = `${req.title} ${req.description ?? ""}`;
    let candidateTaskIds: string[] = [];
    let candidateTasks: { title: string; description: string }[] = [];

    if (tasks.length > 0) {
      try {
        const [vec] = await embeddingProvider.embed([reqText]);
        if (vec) {
          const lit = `[${vec.join(",")}]`;
          // 3b. pgvector similarity against task titles+descriptions
          // We don't have task embeddings, so we'll use a simple text search approach.
          // For now, use token overlap to find candidates (works without task embeddings).
          candidateTasks = tasks.map((t) => ({
            title: t.title,
            description: t.description ?? "",
          }));

          // If we have few tasks, send all as candidates.
          // When we have many, we could use vector search on task text.
          // For now, cap at 5 candidates by token overlap.
          if (tasks.length > 5) {
            const reqTokens = new Set(tokenize(reqText));
            const scored = tasks.map((t) => ({
              task: t,
              score: tokenize(`${t.title} ${t.description ?? ""}`).filter((tok) =>
                reqTokens.has(tok)
              ).length,
            }));
            scored.sort((a, b) => b.score - a.score);
            const top5 = scored.slice(0, 5);
            candidateTasks = top5.map((s) => ({
              title: s.task.title,
              description: s.task.description ?? "",
            }));
            candidateTaskIds = top5.map((s) => s.task.id);
          } else {
            candidateTaskIds = tasks.map((t) => t.id);
          }
        }
      } catch (e) {
        logger.warn({ err: e, requirementId: req.id }, "Audit: embedding failed for requirement");
      }
    }

    // 3c. Call AI provider for judgment
    let judgments: CoverageJudgment[] = [];
    try {
      const result = await provider.auditCoverage({
        requirement: { title: req.title, description: req.description ?? "" },
        candidateTasks,
      });
      judgments = result.judgments;
    } catch (e) {
      logger.warn({ err: e, requirementId: req.id }, "Audit: LLM judgment failed");
      judgments = [{ status: "unclear", rationale: "LLM judgment unavailable." }];
    }

    // Determine overall coverage status for this requirement
    const statuses = judgments.map((j) => j.status);
    let overallStatus: string;
    if (statuses.length === 0 || statuses.every((s) => s === "missing")) {
      overallStatus = "missing";
    } else if (statuses.some((s) => s === "covered")) {
      overallStatus = "covered";
    } else if (statuses.some((s) => s === "partial")) {
      overallStatus = "partial";
    } else {
      overallStatus = "unclear";
    }

    reqCoverageStatus.push({ title: req.title, status: overallStatus });

    // 3d. Write coverage links (preserve user-confirmed)
    for (let i = 0; i < judgments.length && i < candidateTaskIds.length; i++) {
      const taskId = candidateTaskIds[i];
      const judgment = judgments[i];

      // Check if a user-confirmed link already exists
      const existing = await prisma.coverageLink.findFirst({
        where: { requirementId: req.id, taskId },
      });

      if (existing && existing.origin === "user_confirmed") {
        // Skip — user-confirmed links are ground truth
        continue;
      }

      coverageLinksToCreate.push({
        requirementId: req.id,
        taskId,
        status: judgment.status,
        rationale: judgment.rationale,
      });
    }

    // 4. Generate findings
    if (overallStatus === "missing") {
      findingsToCreate.push({
        kind: "uncovered_requirement",
        severity: "critical",
        message: `Requirement "${req.title}" is not covered by any task.`,
        requirementId: req.id,
      });
    } else if (overallStatus === "partial") {
      findingsToCreate.push({
        kind: "partial_coverage",
        severity: "warning",
        message: `Requirement "${req.title}" is only partially covered.`,
        requirementId: req.id,
      });
    } else if (overallStatus === "unclear") {
      findingsToCreate.push({
        kind: "partial_coverage",
        severity: "info",
        message: `Requirement "${req.title}" has unclear coverage — tasks may not be related.`,
        requirementId: req.id,
      });
    }

    // Vague requirement detection
    if (req.title.length < 10 && (!req.description || req.description.length < 20)) {
      findingsToCreate.push({
        kind: "vague_requirement",
        severity: "warning",
        message: `Requirement "${req.title}" is too vague — add more detail.`,
        requirementId: req.id,
      });
    }
  }

  // Orphan task detection (tasks with no requirement link)
  for (const task of tasks) {
    if (!task.requirementId) {
      const hasCoverage = coverageLinksToCreate.some((c) => c.taskId === task.id);
      if (!hasCoverage) {
        // Check if any existing user-confirmed link exists
        const existingLink = await prisma.coverageLink.findFirst({
          where: { taskId: task.id, projectId },
        });
        if (!existingLink) {
          findingsToCreate.push({
            kind: "orphan_task",
            severity: "info",
            message: `Task "${task.title}" is not linked to any requirement.`,
            taskId: task.id,
          });
        }
      }
    }
  }

  // 5. Generate risk summary
  let summary = "";
  try {
    const riskResult = await provider.riskSummary({
      requirements: reqCoverageStatus,
      findings: findingsToCreate.map((f) => ({
        kind: f.kind,
        severity: f.severity,
        message: f.message,
      })),
    });
    summary = riskResult.summary;
  } catch (e) {
    logger.warn({ err: e }, "Audit: risk summary generation failed");
    const covered = reqCoverageStatus.filter((r) => r.status === "covered").length;
    const missing = reqCoverageStatus.filter((r) => r.status === "missing").length;
    summary = `Coverage audit complete. ${covered}/${reqCoverageStatus.length} requirements covered, ${missing} missing. ${findingsToCreate.length} findings.`;
  }

  // 6. Create AuditRun + findings + coverage links
  const auditRun = await prisma.auditRun.create({
    data: {
      projectId,
      userId,
      summary,
      findings: {
        create: findingsToCreate.map((f) => ({
          projectId,
          kind: f.kind as never,
          severity: f.severity as never,
          message: f.message,
          requirementId: f.requirementId,
          taskId: f.taskId,
        })),
      },
    },
  });

  // Write coverage links (delete old AI-suggested ones first, preserve user-confirmed)
  if (coverageLinksToCreate.length > 0) {
    await prisma.coverageLink.deleteMany({
      where: { projectId, origin: "ai_suggested" },
    });
    for (const cl of coverageLinksToCreate) {
      // Check unique constraint — skip if already exists (user-confirmed)
      const existing = await prisma.coverageLink.findFirst({
        where: { requirementId: cl.requirementId, taskId: cl.taskId },
      });
      if (!existing) {
        await prisma.coverageLink.create({
          data: {
            projectId,
            userId,
            requirementId: cl.requirementId,
            taskId: cl.taskId,
            status: cl.status as never,
            origin: "ai_suggested",
            rationale: cl.rationale,
          },
        });
      }
    }
  }

  logger.info(
    { projectId, runId: auditRun.id, findingCount: findingsToCreate.length },
    "Audit: complete"
  );

  return auditRun.id;
}

// ---- Helpers ----

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 3);
}
