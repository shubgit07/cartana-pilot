import type { ChatAskInput, ChatResponse } from "@cartana/shared";
import { apiClient } from "./client";

export const chatApi = {
  ask: (projectId: string, input: ChatAskInput) =>
    apiClient.request<ChatResponse>(`/projects/${projectId}/chat`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
};
