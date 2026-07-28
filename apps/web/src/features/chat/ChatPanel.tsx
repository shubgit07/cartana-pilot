"use client";

import { Card, CardContent } from "@/components/ui/card";
import { ChatHeader } from "./ChatHeader";
import { ChatMessageList } from "./ChatMessageList";
import { ChatComposer } from "./ChatComposer";
import { useChat } from "@/hooks/api";

export function ChatPanel({ projectId }: { projectId: string }) {
  const { messages, sending, error, ask, reset } = useChat(projectId);

  return (
    <Card className="flex h-[70vh] flex-col overflow-hidden">
      <ChatHeader canReset={messages.length > 0} onReset={reset} />
      <CardContent className="flex min-h-0 flex-1 flex-col gap-3 pt-4">
        <ChatMessageList
          messages={messages}
          sending={sending}
          error={error}
          onPickSuggestion={(text) => ask(text)}
        />
        <ChatComposer onSend={(text) => ask(text)} sending={sending} />
      </CardContent>
    </Card>
  );
}
