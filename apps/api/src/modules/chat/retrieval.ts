// Retrieval service — pgvector cosine similarity search over Chunks
// scoped to a project's sources. Returns top-K passages with provenance.

import { prisma } from "../../db/prisma";
import { getEmbeddingProvider } from "../../ai/EmbeddingProvider";

export interface RetrievedPassage {
  chunkId: string;
  sourceId: string;
  filename: string;
  text: string;
  score: number;
}

export async function retrievePassages(params: {
  userId: string;
  projectId: string;
  question: string;
  topK?: number;
}): Promise<RetrievedPassage[]> {
  const { userId, projectId, question, topK = 6 } = params;

  const provider = getEmbeddingProvider();
  const [vec] = await provider.embed([question]);
  if (!vec) return [];

  const lit = `[${vec.join(",")}]`;

  // Cosine distance: pgvector returns <-> for L2, <=> for cosine (1 - cosine_sim).
  // We expose `1 - cosine_distance` as a similarity score in [0,1] (approx).
  const rows = await prisma.$queryRawUnsafe<
    { id: string; sourceId: string; text: string; filename: string; score: number }[]
  >(
    `
    SELECT
      c.id          AS "id",
      c."sourceId"  AS "sourceId",
      c.text        AS "text",
      s.filename    AS "filename",
      1 - (c.embedding <=> $1::vector) AS "score"
    FROM "Chunk" c
    JOIN "Source" s ON s.id = c."sourceId"
    WHERE c.embedding IS NOT NULL
      AND s."projectId" = $2
      AND s."userId" = $3
    ORDER BY c.embedding <=> $1::vector
    LIMIT $4
    `,
    lit,
    projectId,
    userId,
    topK
  );

  return rows.map((r) => ({
    chunkId: r.id,
    sourceId: r.sourceId,
    filename: r.filename,
    text: r.text,
    score: Number(r.score),
  }));
}