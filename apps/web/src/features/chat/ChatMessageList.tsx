"use client";

import * as React from "react";
import { ChatMessage } from "./ChatMessage";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { useChatScroll } from "./useChatScroll";
import type { ChatMessage as ChatMessageT } from "@cartana/shared";

type Props = {
  messages: ChatMessageT[];
  sending: boolean;
  error: string | null;
  onPickSuggestion: (text: string) => void;
};

export function ChatMessageList({ messages, sending, error, onPickSuggestion }: Props) {
  const ref = useChatScroll([messages.length, sending]);

  if (messages.length === 0) {
    return (
      <div
        ref={ref}
        className="scrollbar-thin min-h-0 flex-1 space-y-3 overflow-y-auto rounded-xl border border-border/70 bg-surface-sunken p-4"
      >
        <SuggestedQuestions onPick={onPickSuggestion} />
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="scrollbar-thin min-h-0 flex-1 space-y-4 overflow-y-auto rounded-xl border border-border/70 bg-surface-sunken p-4"
    >
      {messages.map((m, i) => (
        <ChatMessage key={i} message={m} />
      ))}
      {sending && (
        <div
          className="flex items-center gap-2.5 text-sm text-muted-foreground"
          aria-live="polite"
        >
          {/* Typing indicator — three staggered dots read as calmer than a spinner. */}
          <span className="flex items-center gap-1" aria-hidden="true">
            <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground/70 [animation-delay:-0.3s]" />
            <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground/70 [animation-delay:-0.15s]" />
            <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground/70" />
          </span>
          Thinking…
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-xs leading-relaxed text-danger-soft-foreground"
        >
          {error}
        </div>
      )}
    </div>
  );
}
