"use client";

import * as React from "react";
import type { ChatCitation } from "@cartana/shared";
import { Badge } from "@/components/ui/badge";
import { formatScore } from "@/lib/format";
import { FileText } from "lucide-react";

export function ChatCitations({ citations }: { citations: ChatCitation[] }) {
  if (!citations || citations.length === 0) return null;
  return (
    <section
      aria-label={`Sources for this answer (${citations.length})`}
      className="mt-2.5 space-y-2 border-t border-border/70 pt-2.5"
    >
      <header className="eyebrow flex items-center gap-1.5">
        <FileText className="h-3 w-3" aria-hidden="true" />
        Sources · {citations.length}
      </header>
      <ol className="space-y-1.5 text-xs">
        {citations.map((c, i) => (
          <li
            key={c.chunkId}
            className={cn(
              "rounded-lg border border-border/70 bg-surface-sunken p-2.5",
              "transition-colors duration-150 hover:border-border-strong"
            )}
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5 font-medium">
                <span
                  aria-hidden="true"
                  className="grid size-4 shrink-0 place-items-center rounded bg-muted font-mono text-[10px] text-muted-foreground"
                >
                  {i + 1}
                </span>
                <span className="truncate">{c.filename}</span>
              </span>
              <Badge variant="muted" className="shrink-0">
                <span className="tabular">{formatScore(c.score)}</span>
              </Badge>
            </div>
            <div className="break-words leading-relaxed text-muted-foreground">{c.snippet}</div>
          </li>
        ))}
      </ol>
    </section>
  );
}
import { cn } from "@/lib/cn";
