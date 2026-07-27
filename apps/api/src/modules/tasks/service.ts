// Task service — DB queries + idempotent upsert used by the extraction job.

import { prisma } from "../../db/prisma";
import { dedupeKey } from "../../lib/dedupe";
import { TaskDetail, TaskSummary } from "@cartana/shared";
import { NotFoundError } from "../../lib/errors";

interface ChunkLink {
  chunkId: string;
  sourceId: string;
  filename: string;
  snippet: string;
}

interface SourceLink {
  sourceId: string;
  filename: string;
}

async function loadChunkLinksForTasks(taskIds: string[]): Promise<Map<string, ChunkLink[]>> {
  const map = new Map<string, ChunkLink[]>();
  if (taskIds.length === 0) return map;
  const links = await prisma.taskChunk.findMany({
    where: { taskId: { in: taskIds } },
    include: {
      chunk: {
        select: {
          id: true,
          text: true,
          source: { select: { id: true, filename: true } },
        },
      },
    },
  });
  for (const l of links) {
    const arr = map.get(l.taskId) ?? [];
    arr.push({
      chunkId: l.chunk.id,
      sourceId: l.chunk.source.id,
      filename: l.chunk.source.filename,
      snippet: l.chunk.text.length > 240 ? l.chunk.text.slice(0, 240) + "…" : l.chunk.text,
    });
    map.set(l.taskId, arr);
  }
  return map;
}

async function loadSourceLinksByTask(
  taskIds: string[]
): Promise<Map<string, SourceLink[]>> {
  const map = new Map<string, SourceLink[]>();
  if (taskIds.length === 0) return map;
  const links = await prisma.taskChunk.findMany({
    where: { taskId: { in: taskIds } },
    include: { chunk: { include: { source: { select: { id: true, filename: true } } } } },
  });
  const seen = new Map<string, Set<string>>();
  for (const l of links) {
    const sid = l.chunk.source.id;
    const fname = l.chunk.source.filename;
    const reqSet = seen.get(l.taskId) ?? new Set<string>();
    if (!reqSet.has(sid)) {
      reqSet.add(sid);
      const arr = map.get(l.taskId) ?? [];
      arr.push({ sourceId: sid, filename: fname });
      map.set(l.taskId, arr);
    }
  }
  return map;
}

function toSummary(
  t: {
    id: string;
    projectId: string;
    requirementId: string | null;
    title: string;
    description: string | null;
    origin: "ai" | "user";
    state: "suggested" | "accepted" | "rejected" | "edited";
    createdAt: Date;
    updatedAt: Date;
    requirement?: { title: string } | null;
  },
  sourceLinks: SourceLink[]
): TaskSummary {
  return {
    id: t.id,
    projectId: t.projectId,
    requirementId: t.requirementId,
    requirementTitle: t.requirement?.title ?? null,
    title: t.title,
    description: t.description,
    origin: t.origin,
    state: t.state,
    sourceLinks,
    createdAt: t.createdAt.toISOString(),
    updatedAt: t.updatedAt.toISOString(),
  };
}

export async function listTasks(userId: string, projectId: string): Promise<TaskSummary[]> {
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const rows = await prisma.task.findMany({
    where: { projectId, userId },
    orderBy: [{ state: "asc" }, { createdAt: "desc" }],
    include: { requirement: { select: { title: true } } },
  });
  if (rows.length === 0) return [];

  const linkMap = await loadSourceLinksByTask(rows.map((r) => r.id));
  return rows.map((r) => toSummary(r, linkMap.get(r.id) ?? []));
}

export async function getTask(
  userId: string,
  projectId: string,
  id: string
): Promise<TaskDetail> {
  const row = await prisma.task.findFirst({
    where: { id, projectId, userId },
    include: { requirement: { select: { title: true } } },
  });
  if (!row) throw new NotFoundError("Task not found");

  const linkMap = await loadSourceLinksByTask([row.id]);
  const chunkMap = await loadChunkLinksForTasks([row.id]);
  return {
    ...toSummary(row, linkMap.get(row.id) ?? []),
    chunkLinks: chunkMap.get(row.id) ?? [],
  };
}

export async function createTask(
  userId: string,
  projectId: string,
  input: { title: string; description?: string | null; requirementId?: string | null }
) {
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  if (input.requirementId) {
    const r = await prisma.requirement.findFirst({
      where: { id: input.requirementId, projectId, userId },
    });
    if (!r) throw new NotFoundError("Linked requirement not found in this project");
  }

  return prisma.task.create({
    data: {
      projectId,
      userId,
      title: input.title,
      description: input.description ?? null,
      requirementId: input.requirementId ?? null,
      origin: "user",
      state: "accepted",
    },
    include: { requirement: { select: { title: true } } },
  });
}

export async function updateTask(
  userId: string,
  projectId: string,
  id: string,
  input: {
    title?: string;
    description?: string | null;
    state?: "suggested" | "accepted" | "rejected" | "edited";
    requirementId?: string | null;
  }
) {
  const row = await prisma.task.findFirst({ where: { id, projectId, userId } });
  if (!row) throw new NotFoundError("Task not found");

  if (input.requirementId) {
    const r = await prisma.requirement.findFirst({
      where: { id: input.requirementId, projectId, userId },
    });
    if (!r) throw new NotFoundError("Linked requirement not found in this project");
  }

  const nextState = input.state ?? row.state;
  const touched =
    input.title !== undefined ||
    input.description !== undefined ||
    input.state !== undefined ||
    input.requirementId !== undefined;
  const finalState: "suggested" | "accepted" | "rejected" | "edited" =
    touched && nextState === "suggested" && row.origin === "ai" ? "edited" : nextState;

  return prisma.task.update({
    where: { id },
    data: {
      ...(input.title !== undefined ? { title: input.title } : {}),
      ...(input.description !== undefined ? { description: input.description } : {}),
      ...(input.requirementId !== undefined ? { requirementId: input.requirementId } : {}),
      state: finalState,
      origin: row.origin === "ai" && touched ? "user" : row.origin,
    },
    include: { requirement: { select: { title: true } } },
  });
}

export async function deleteTask(userId: string, projectId: string, id: string) {
  const row = await prisma.task.findFirst({ where: { id, projectId, userId } });
  if (!row) throw new NotFoundError("Task not found");
  await prisma.task.delete({ where: { id } });
}

// -------------------------------------------------------------------------
// Idempotent upsert used by the extraction job.
// -------------------------------------------------------------------------

export interface TaskUpsert {
  sourceId: string;
  title: string;
  description: string;
  chunkIds: string[];
  linkedRequirementTitle?: string;
}

export async function upsertTaskFromExtraction(params: {
  userId: string;
  projectId: string;
  item: TaskUpsert;
  requirementIdByTitle: Map<string, string>;
}) {
  const { userId, projectId, item, requirementIdByTitle } = params;
  const key = dedupeKey(item.sourceId, item.title);

  const existing = await prisma.task.findFirst({ where: { dedupeKey: key, projectId } });
  const linkedReqId = item.linkedRequirementTitle
    ? requirementIdByTitle.get(item.linkedRequirementTitle.toLowerCase()) ?? null
    : null;

  if (!existing) {
    return prisma.task.create({
      data: {
        projectId,
        userId,
        title: item.title,
        description: item.description,
        origin: "ai",
        state: "suggested",
        dedupeKey: key,
        requirementId: linkedReqId,
        chunks: {
          create: dedupeValidChunkIds(item.chunkIds).map((chunkId) => ({
            chunk: { connect: { id: chunkId } },
          })),
        },
      },
    });
  }

  if (existing.state !== "suggested" || existing.origin !== "ai") {
    return existing;
  }

  await prisma.taskChunk.deleteMany({ where: { taskId: existing.id } });
  await prisma.taskChunk.createMany({
    data: dedupeValidChunkIds(item.chunkIds).map((chunkId) => ({
      taskId: existing.id,
      chunkId,
    })),
    skipDuplicates: true,
  });
  return prisma.task.update({
    where: { id: existing.id },
    data: {
      title: item.title,
      description: item.description,
      // Only auto-relink if the task had no requirement yet; respect manual relinks.
      requirementId: existing.requirementId ?? linkedReqId,
    },
  });
}

/**
 * Mark AI-suggested tasks for `sourceId` whose dedupeKey is NOT in the freshly
 * extracted set as state=rejected.
 */
export async function staleOutAITasks(params: {
  userId: string;
  projectId: string;
  sourceId: string;
  freshKeys: Set<string>;
}) {
  const { userId, projectId, sourceId, freshKeys } = params;
  const links = await prisma.taskChunk.findMany({
    where: { chunk: { sourceId } },
    include: { task: true },
  });

  const staleIds = new Set<string>();
  for (const l of links) {
    const t = l.task;
    if (t.origin !== "ai" || t.state !== "suggested") continue;
    if (!t.dedupeKey || !freshKeys.has(t.dedupeKey)) staleIds.add(t.id);
  }

  if (staleIds.size === 0) return 0;
  await prisma.task.updateMany({
    where: { id: { in: Array.from(staleIds) }, userId, projectId },
    data: { state: "rejected" },
  });
  return staleIds.size;
}

function dedupeValidChunkIds(ids: string[]): string[] {
  return Array.from(new Set(ids.filter(Boolean)));
}