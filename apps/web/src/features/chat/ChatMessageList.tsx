"use client";

import * as React from "react";
import { ChatMessage } from "./ChatMessage";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { useChatScroll } from "./useChatScroll";
import { Loader2 } from "lucide-react";
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
        className="scrollbar-thin min-h-0 flex-1 space-y-3 overflow-y-auto rounded-md border bg-muted/30 p-4"
      >
        <SuggestedQuestions onPick={onPickSuggestion} />
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="scrollbar-thin min-h-0 flex-1 space-y-4 overflow-y-auto rounded-md border bg-muted/30 p-4"
    >
      {messages.map((m, i) => (
        <ChatMessage key={i} message={m} />
      ))}
      {sending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          Thinking…
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}
