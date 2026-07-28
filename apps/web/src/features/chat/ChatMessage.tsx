"use client";

import * as React from "react";
import type { ChatMessage as ChatMessageT } from "@cartana/shared";
import { ChatCitations } from "./ChatCitations";
import { cn } from "@/lib/cn";

export function ChatMessage({ message }: { message: ChatMessageT }) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "animate-slide-up",
        isUser ? "flex justify-end" : "flex justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[82%] space-y-2 rounded-xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "rounded-br-sm bg-primary-soft text-primary-soft-foreground"
            : "rounded-bl-sm border border-border bg-card text-card-foreground shadow-card"
        )}
      >
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
        {!isUser && message.citations && (
          <ChatCitations citations={message.citations} />
        )}
      </div>
    </div>
  );
}
