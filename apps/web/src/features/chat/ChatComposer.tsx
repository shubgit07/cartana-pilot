"use client";

import * as React from "react";
import { Loader2, SendHorizonal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

type Props = {
  onSend: (text: string) => void;
  sending: boolean;
};

export function ChatComposer({ onSend, sending }: Props) {
  const [value, setValue] = React.useState("");
  const ref = React.useRef<HTMLTextAreaElement | null>(null);
  const canSend = value.trim().length > 0 && !sending;

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

      {/* Unified composer well — textarea and action read as one control. */}
      <div
        className={cn(
          "flex items-end gap-2 rounded-xl border border-input bg-surface p-2 shadow-soft",
          "transition-[border-color,box-shadow] duration-150 ease-out-expo",
          "focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/25"
        )}
      >
        <textarea
          id="chat-input"
          name="chatInput"
          ref={ref}
          placeholder="Ask a question about your project material…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          maxLength={4000}
          className={cn(
            "min-h-[52px] w-full resize-none bg-transparent px-2 py-1.5 text-sm leading-relaxed text-foreground",
            "placeholder:text-muted-foreground/80",
            "focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          )}
          aria-label="Ask a question about your project material"
          spellCheck
          autoComplete="off"
        />
        <Button
          type="button"
          onClick={submit}
          disabled={!canSend}
          size="icon"
          className="shrink-0"
          aria-label={sending ? "Sending…" : "Send message"}
        >
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <SendHorizonal className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </div>

      <p className="mt-1.5 text-xs text-muted-foreground/80">
        <kbd className="rounded border border-border bg-surface-sunken px-1.5 py-0.5 font-sans text-2xs">
          Enter
        </kbd>{" "}
        to send ·{" "}
        <kbd className="rounded border border-border bg-surface-sunken px-1.5 py-0.5 font-sans text-2xs">
          Shift + Enter
        </kbd>{" "}
        for a new line
      </p>
    </div>
  );
}
