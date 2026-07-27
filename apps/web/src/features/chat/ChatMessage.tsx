"use client";

import * as React from "react";
import type { ChatMessage as ChatMessageT } from "@cartana/shared";
import { ChatCitations } from "./ChatCitations";
import { cn } from "@/lib/cn";

export function ChatMessage({ message }: { message: ChatMessageT }) {
  const isUser = message.role === "user";
  return (
    <div className={cn(isUser ? "flex justify-end" : "flex justify-start")}>
      <div
        className={cn(
          "max-w-[80%] space-y-2 rounded-lg px-3 py-2 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border bg-background text-foreground"
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
