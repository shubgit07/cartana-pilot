"use client";

import * as React from "react";
import { Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  onSend: (text: string) => void;
  sending: boolean;
};

export function ChatComposer({ onSend, sending }: Props) {
  const [value, setValue] = React.useState("");
  const ref = React.useRef<HTMLTextAreaElement | null>(null);

  function submit() {
    const text = value.trim();
    if (!text || sending) return;
    setValue("");
    onSend(text);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div>
      <label htmlFor="chat-input" className="sr-only">
        Ask a question
      </label>
      <div className="flex items-end gap-2">
        <Textarea
          id="chat-input"
          name="chatInput"
          ref={ref}
          placeholder="Ask a question about your project material…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          maxLength={4000}
          className="resize-none"
          aria-label="Ask a question about your project material"
          spellCheck
          autoComplete="off"
        />
        <Button
          type="button"
          onClick={submit}
          disabled={!value.trim() || sending}
          size="lg"
          aria-label={sending ? "Sending…" : "Send message"}
        >
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        <kbd className="rounded border bg-muted px-1 tabular">Enter</kbd> to send ·{" "}
        <kbd className="rounded border bg-muted px-1">Shift</kbd> +{" "}
        <kbd className="rounded border bg-muted px-1 tabular">Enter</kbd> for a new line
      </p>
    </div>
  );
}
