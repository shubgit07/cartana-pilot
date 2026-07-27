// Chat service — retrieval + generation. Routes are thin.

import { ChatAskInput, ChatMessage, ChatResponse } from "@cartana/shared";
import { retrievePassages } from "./retrieval";
import { getAIProvider } from "../../ai/AIProvider";
import { NotFoundError } from "../../lib/errors";
import { prisma } from "../../db/prisma";

export async function askProject(userId: string, projectId: string, input: ChatAskInput): Promise<ChatResponse> {
  // Verify project ownership (404 hides existence from other users)
  const project = await prisma.project.findFirst({ where: { id: projectId, userId } });
  if (!project) throw new NotFoundError("Project not found");

  const passages = await retrievePassages({ userId, projectId, question: input.question });

  const ai = getAIProvider();
  const out = await ai.chat({
    question: input.question,
    history: input.history ?? [],
    passages: passages.map((p) => ({
      chunkId: p.chunkId,
      sourceId: p.sourceId,
      filename: p.filename,
      text: p.text,
      score: p.score,
    })),
  });

  const message: ChatMessage = {
    role: "assistant",
    content: out.answer,
    citations: out.citations,
    createdAt: new Date().toISOString(),
  };
  return { message };
}