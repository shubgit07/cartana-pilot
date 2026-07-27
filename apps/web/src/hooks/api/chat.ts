"use client";

import * as React from "react";
import { chatApi } from "@/lib/api";
import type { ChatMessage } from "@cartana/shared";
import { messageOf } from "./projects";

const STORAGE_PREFIX = "cartana:chat:";

function readStored(projectId: string): ChatMessage[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + projectId);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return null;
    return parsed as ChatMessage[];
  } catch {
    return null;
  }
}

function writeStored(projectId: string, messages: ChatMessage[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_PREFIX + projectId, JSON.stringify(messages));
  } catch {
    // quota / private mode — ignore
  }
}

export function useChat(projectId: string) {
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [hydrated, setHydrated] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setHydrated(true);
    setMessages(readStored(projectId) ?? []);
  }, [projectId]);

  React.useEffect(() => {
    if (!hydrated) return;
    writeStored(projectId, messages);
  }, [hydrated, projectId, messages]);

  const ask = React.useCallback(
    async (question: string) => {
      if (!question.trim() || sending) return;
      setSending(true);
      setError(null);

      const userMsg: ChatMessage = {
        role: "user",
        content: question,
        createdAt: new Date().toISOString(),
      };

      // Functional updater — avoids the stale-closure race on `messages`.
      setMessages((prev) => [...prev, userMsg]);

      try {
        let history: { role: "user" | "assistant"; content: string }[] = [];
        setMessages((prev) => {
          history = prev.slice(0, -1).map((m) => ({ role: m.role, content: m.content }));
          return prev;
        });

        const res = await chatApi.ask(projectId, { question, history });
        setMessages((prev) => [...prev, res.message]);
      } catch (e: unknown) {
        setError(messageOf(e) ?? "Chat request failed");
      } finally {
        setSending(false);
      }
    },
    [projectId, sending]
  );

  const reset = React.useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sending, error, ask, reset };
}
