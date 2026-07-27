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
      className="mt-2 space-y-2 border-t pt-2"
    >
      <header className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
        Sources ({citations.length})
      </header>
      <ol className="space-y-1.5 text-xs">
        {citations.map((c, i) => (
          <li key={c.chunkId} className="rounded-md border bg-muted/40 p-2">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-medium">
                [{i + 1}] {c.filename}
              </span>
              <Badge variant="muted">
                score <span className="tabular">{formatScore(c.score)}</span>
              </Badge>
            </div>
            <div className="break-words text-muted-foreground">{c.snippet}</div>
          </li>
        ))}
      </ol>
    </section>
  );
}
