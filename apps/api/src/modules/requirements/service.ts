// Requirement service — DB queries + idempotent upsert helper used by the
// extraction job. Public read methods are also exported for the router.

import { prisma } from "../../db/prisma";
import { dedupeKey } from "../../lib/dedupe";
import { RequirementDetail, RequirementSummary } from "@cartana/shared";
import { NotFoundError } from "../../lib/errors";

interface ChunkLink {
  chunkId: string;
  sourceId: string;
  filename: string;
  snippet: string;
}

async function chunksToLinks(
  chunkLinks: { chunkId: string; sourceId: string; filename: string; snippet: string }[]
): Promise<ChunkLink[]> {
  return chunkLinks;
}

// Pull chunk links for a list of requirements in one query.
async function loadChunkLinksForRequirements(
  requirementIds: string[]
): Promise<Map<string, ChunkLink[]>> {
  const map = new Map<string, ChunkLink[]>();
  if (requirementIds.length === 0) return map;
  const links = await prisma.requirementChunk.findMany({
    where: { requirementId: { in: requirementIds } },
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
    const arr = map.get(l.requirementId) ?? [];
    arr.push({
      chunkId: l.chunk.id,
      sourceId: l.chunk.source.id,
      filename: l.chunk.source.filename,
      snippet: l.chunk.text.length > 240 ? l.chunk.text.slice(0, 240) + "…" : l.chunk.text,
    });
    map.set(l.requirementId, arr);
  }
  return map;
}

function toSummary(
  r: {
    id: string;
    projectId: string;
    title: string;
    description: string | null;
    origin: "ai" | "user";
    state: "suggested" | "accepted" | "rejected" | "edited";
    createdAt: Date;
    updatedAt: Date;
  },
  sourceLinks: { sourceId: string; filename: string }[]
): RequirementSummary {
  return {
    id: r.id,
    projectId: r.projectId,
    title: r.title,
    description: r.description,
    origin: r.origin,
    state: r.state,
    sourceLinks,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  };
}

export async function listRequirements(
  userId: string,
  projectId: string
): Promise<RequirementSummary[]> {
  // Ensure ownership
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const rows = await prisma.requirement.findMany({
    where: { projectId, userId },
    orderBy: [{ state: "asc" }, { createdAt: "desc" }],
  });
  if (rows.length === 0) return [];

  const linkMap = await loadChunkLinksForRequirements(rows.map((r) => r.id));
  const sourcesMap = await loadSourceLinksByRequirement(rows.map((r) => r.id));

  return rows.map((r) => toSummary(r, sourcesMap.get(r.id) ?? []));
}

async function loadSourceLinksByRequirement(
  requirementIds: string[]
): Promise<Map<string, { sourceId: string; filename: string }[]>> {
  const map = new Map<string, { sourceId: string; filename: string }[]>();
  if (requirementIds.length === 0) return map;
  const links = await prisma.requirementChunk.findMany({
    where: { requirementId: { in: requirementIds } },
    include: { chunk: { include: { source: { select: { id: true, filename: true } } } } },
  });
  const seen = new Map<string, Set<string>>(); // reqId -> set of sourceIds
  for (const l of links) {
    const sourceId = l.chunk.source.id;
    const filename = l.chunk.source.filename;
    const reqSet = seen.get(l.requirementId) ?? new Set<string>();
    if (!reqSet.has(sourceId)) {
      reqSet.add(sourceId);
      const arr = map.get(l.requirementId) ?? [];
      arr.push({ sourceId, filename });
      map.set(l.requirementId, arr);
    }
  }
  return map;
}

export async function getRequirement(
  userId: string,
  projectId: string,
  id: string
): Promise<RequirementDetail> {
  const row = await prisma.requirement.findFirst({ where: { id, projectId, userId } });
  if (!row) throw new NotFoundError("Requirement not found");

  const linkMap = await loadChunkLinksForRequirements([row.id]);
  const sourcesMap = await loadSourceLinksByRequirement([row.id]);
  const summary = toSummary(row, sourcesMap.get(row.id) ?? []);
  return {
    ...summary,
    chunkLinks: linkMap.get(row.id) ?? [],
  };
}

export async function updateRequirement(
  userId: string,
  projectId: string,
  id: string,
  input: {
    title?: string;
    description?: string | null;
    state?: "suggested" | "accepted" | "rejected" | "edited";
  }
) {
  const row = await prisma.requirement.findFirst({ where: { id, projectId, userId } });
  if (!row) throw new NotFoundError("Requirement not found");

  // Switching state to accepted/rejected/edited counts as a user touch.
  const nextState = input.state ?? row.state;
  const touched =
    input.title !== undefined ||
    input.description !== undefined ||
    input.state !== undefined;
  const finalState: "suggested" | "accepted" | "rejected" | "edited" =
    touched && nextState === "suggested" && row.origin === "ai"
      ? "edited"
      : nextState;

  const updated = await prisma.requirement.update({
    where: { id },
    data: {
      ...(input.title !== undefined ? { title: input.title } : {}),
      ...(input.description !== undefined ? { description: input.description } : {}),
      state: finalState,
      // Preserve user ownership: if a user edits an AI suggestion, it becomes user-owned.
      origin: row.origin === "ai" && touched ? "user" : row.origin,
    },
  });
  return updated;
}

export async function deleteRequirement(userId: string, projectId: string, id: string) {
  const row = await prisma.requirement.findFirst({ where: { id, projectId, userId } });
  if (!row) throw new NotFoundError("Requirement not found");
  await prisma.requirement.delete({ where: { id } });
}

// -------------------------------------------------------------------------
// Idempotent upsert used by the extraction job.
// -------------------------------------------------------------------------

export interface RequirementUpsert {
  sourceId: string;
  title: string;
  description: string;
  chunkIds: string[];
}

export async function upsertRequirementFromExtraction(params: {
  userId: string;
  projectId: string;
  item: RequirementUpsert;
}) {
  const { userId, projectId, item } = params;
  const key = dedupeKey(item.sourceId, item.title);

  const existing = await prisma.requirement.findFirst({
    where: { dedupeKey: key, projectId },
  });

  if (!existing) {
    // Brand new. Create + link chunks.
    return prisma.requirement.create({
      data: {
        projectId,
        userId,
        title: item.title,
        description: item.description,
        origin: "ai",
        state: "suggested",
        dedupeKey: key,
        chunks: {
          create: dedupeValidChunkIds(item.chunkIds).map((chunkId) => ({
            chunk: { connect: { id: chunkId } },
          })),
        },
      },
    });
  }

  // Already exists. If user has touched it (accepted/rejected/edited),
  // leave it alone — only refresh the chunk links if they actually differ.
  if (existing.state !== "suggested" || existing.origin !== "ai") {
    return existing;
  }

  // Still AI-suggested and untouched. Refresh content + chunk links.
  await prisma.requirementChunk.deleteMany({ where: { requirementId: existing.id } });
  await prisma.requirementChunk.createMany({
    data: dedupeValidChunkIds(item.chunkIds).map((chunkId) => ({
      requirementId: existing.id,
      chunkId,
    })),
    skipDuplicates: true,
  });
  return prisma.requirement.update({
    where: { id: existing.id },
    data: { title: item.title, description: item.description },
  });
}

/**
 * Mark any AI-suggested requirement for `sourceId` whose dedupeKey is NOT in
 * the freshly-extracted set as state=rejected (preserves them in DB but
 * filters them out of the active list).
 */
export async function staleOutAIRequirements(params: {
  userId: string;
  projectId: string;
  sourceId: string;
  freshKeys: Set<string>;
}) {
  const { userId, projectId, sourceId, freshKeys } = params;
  // Pull all ai/suggested requirements for this source via the chunk links.
  const links = await prisma.requirementChunk.findMany({
    where: { chunk: { sourceId } },
    include: { requirement: true },
  });

  const staleIds = new Set<string>();
  for (const l of links) {
    const r = l.requirement;
    if (r.origin !== "ai" || r.state !== "suggested") continue;
    if (!r.dedupeKey || !freshKeys.has(r.dedupeKey)) staleIds.add(r.id);
  }

  if (staleIds.size === 0) return 0;
  await prisma.requirement.updateMany({
    where: { id: { in: Array.from(staleIds) }, userId, projectId },
    data: { state: "rejected" },
  });
  return staleIds.size;
}

function dedupeValidChunkIds(ids: string[]): string[] {
  return Array.from(new Set(ids.filter(Boolean)));
}