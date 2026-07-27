// Project module — service only (DB access lives here).
// Routes are thin and call into this.

import { prisma } from "../../db/prisma";
import {
  CreateProjectInput,
  ProjectDetail,
  ProjectSummary,
  SourceSummary,
  UpdateProjectInput,
} from "@cartana/shared";
import { NotFoundError } from "../../lib/errors";

function toSummary(p: {
  id: string;
  name: string;
  description: string | null;
  createdAt: Date;
  _count: { sources: number };
}): ProjectSummary {
  return {
    id: p.id,
    name: p.name,
    description: p.description,
    createdAt: p.createdAt.toISOString(),
    sourceCount: p._count.sources,
  };
}

function toSourceSummary(s: {
  id: string;
  projectId: string;
  filename: string;
  kind: "pdf" | "text";
  status: "uploaded" | "processing" | "processed" | "failed";
  errorMessage: string | null;
  createdAt: Date;
  _count: { chunks: number };
}): SourceSummary {
  return {
    id: s.id,
    projectId: s.projectId,
    filename: s.filename,
    kind: s.kind,
    status: s.status,
    errorMessage: s.errorMessage,
    createdAt: s.createdAt.toISOString(),
    chunkCount: s._count.chunks,
  };
}

export async function listProjects(userId: string): Promise<ProjectSummary[]> {
  const rows = await prisma.project.findMany({
    where: { userId },
    orderBy: { createdAt: "desc" },
    include: { _count: { select: { sources: true } } },
  });
  return rows.map(toSummary);
}

export async function getProject(userId: string, id: string): Promise<ProjectDetail> {
  const row = await prisma.project.findFirst({
    where: { id, userId },
    include: {
      _count: { select: { sources: true } },
      sources: {
        orderBy: { createdAt: "desc" },
        include: { _count: { select: { chunks: true } } },
      },
    },
  });
  if (!row) throw new NotFoundError("Project not found");
  return {
    ...toSummary(row),
    sources: row.sources.map(toSourceSummary),
  };
}

export async function createProject(userId: string, input: CreateProjectInput): Promise<ProjectSummary> {
  const row = await prisma.project.create({
    data: {
      userId,
      name: input.name,
      description: input.description ?? null,
    },
    include: { _count: { select: { sources: true } } },
  });
  return toSummary(row);
}

export async function updateProject(
  userId: string,
  id: string,
  input: UpdateProjectInput
): Promise<ProjectSummary> {
  // Ensure ownership
  await getProject(userId, id);
  const row = await prisma.project.update({
    where: { id },
    data: {
      ...(input.name !== undefined ? { name: input.name } : {}),
      ...(input.description !== undefined ? { description: input.description } : {}),
    },
    include: { _count: { select: { sources: true } } },
  });
  return toSummary(row);
}

export async function deleteProject(userId: string, id: string): Promise<void> {
  await getProject(userId, id);
  await prisma.project.delete({ where: { id } });
}