// Source service — DB + storage operations for uploaded sources.
// Background processing kicks off via the queue, NOT in this file.

import { prisma } from "../../db/prisma";
import { getStorage } from "../../storage/StorageProvider";
import { sourceIngestQueue } from "../../queue/queues";
import { NotFoundError, ValidationError } from "../../lib/errors";
import { SourceKind, SourceSummary } from "@cartana/shared";

function inferKind(filename: string, mimeType?: string): SourceKind {
  const fn = filename.toLowerCase();
  if (fn.endsWith(".pdf") || mimeType === "application/pdf") return "pdf";
  if (
    fn.endsWith(".txt") ||
    fn.endsWith(".md") ||
    fn.endsWith(".markdown") ||
    (mimeType ?? "").startsWith("text/")
  ) {
    return "text";
  }
  throw new ValidationError(`Unsupported file type: ${filename} (${mimeType ?? "unknown"})`);
}

export async function createSourceFromFile(params: {
  userId: string;
  projectId: string;
  filename: string;
  mimeType?: string;
  data: Buffer;
}): Promise<SourceSummary> {
  const { userId, projectId, filename, mimeType, data } = params;
  // Ensure project belongs to user
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const kind = inferKind(filename, mimeType);
  const storage = getStorage();
  const safeName = filename.replace(/[^A-Za-z0-9._-]/g, "_");
  const keyHint = `projects/${projectId}/${Date.now()}-${safeName}`;
  const storageKey = await storage.put(keyHint, data);

  const row = await prisma.source.create({
    data: {
      projectId,
      userId,
      filename,
      kind,
      storageKey,
      mimeType: mimeType ?? null,
      sizeBytes: data.length,
      status: "uploaded",
    },
    include: { _count: { select: { chunks: true } } },
  });

  // Kick off async ingestion.
  await sourceIngestQueue.add(
    "ingest",
    { sourceId: row.id, projectId, userId },
    { jobId: `ingest-${row.id}` }
  );

  return toSummary(row);
}

export async function createSourceFromText(params: {
  userId: string;
  projectId: string;
  filename: string;
  content: string;
}): Promise<SourceSummary> {
  const { userId, projectId, filename, content } = params;
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const storage = getStorage();
  const safeName = filename.replace(/[^A-Za-z0-9._-]/g, "_");
  const keyHint = `projects/${projectId}/${Date.now()}-${safeName}`;
  const storageKey = await storage.put(keyHint, Buffer.from(content, "utf8"));

  const row = await prisma.source.create({
    data: {
      projectId,
      userId,
      filename,
      kind: "text",
      storageKey,
      mimeType: "text/plain",
      sizeBytes: Buffer.byteLength(content, "utf8"),
      status: "uploaded",
    },
    include: { _count: { select: { chunks: true } } },
  });

  await sourceIngestQueue.add(
    "ingest",
    { sourceId: row.id, projectId, userId },
    { jobId: `ingest-${row.id}` }
  );

  return toSummary(row);
}

export async function listSources(userId: string, projectId: string): Promise<SourceSummary[]> {
  const rows = await prisma.source.findMany({
    where: { projectId, userId },
    orderBy: { createdAt: "desc" },
    include: { _count: { select: { chunks: true } } },
  });
  return rows.map(toSummary);
}

export async function getSource(userId: string, sourceId: string): Promise<SourceSummary> {
  const row = await prisma.source.findFirst({
    where: { id: sourceId, userId },
    include: { _count: { select: { chunks: true } } },
  });
  if (!row) throw new NotFoundError("Source not found");
  return toSummary(row);
}

export async function getSourceJobStatus(userId: string, sourceId: string) {
  const row = await prisma.source.findFirst({
    where: { id: sourceId, userId },
    include: {
      _count: { select: { chunks: true } },
      chunks: { select: { id: true, embedding: true } },
    },
  });
  if (!row) throw new NotFoundError("Source not found");
  const chunksTotal = row._count.chunks;
  const embedded = row.chunks.filter((c) => c.embedding != null).length;
  return {
    sourceId: row.id,
    status: row.status,
    chunksTotal,
    embedded,
    errorMessage: row.errorMessage,
  };
}

export async function deleteSource(userId: string, sourceId: string): Promise<void> {
  const row = await prisma.source.findFirst({ where: { id: sourceId, userId } });
  if (!row) throw new NotFoundError("Source not found");
  const storage = getStorage();
  await storage.remove(row.storageKey).catch(() => {});
  await prisma.source.delete({ where: { id: sourceId } });
}

function toSummary(s: {
  id: string;
  projectId: string;
  filename: string;
  kind: SourceKind;
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