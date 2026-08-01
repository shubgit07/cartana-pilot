"use client";

import * as React from "react";
import { FileText, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SourceStatusBadge } from "./SourceStatusBadge";
import { useSourceStatus } from "@/hooks/api";

type Props = {
  projectId: string;
  sourceId: string;
  filename: string;
  kind: "pdf" | "text";
  status: "uploaded" | "processing" | "processed" | "failed";
  chunkCount: number;
  errorMessage: string | null;
  onDelete: () => void;
};

export function SourceRow({
  projectId,
  sourceId,
  filename,
  kind,
  status,
  chunkCount,
  errorMessage,
  onDelete,
}: Props) {
  const poll = status === "processed" ? null : sourceId;
  const live = useSourceStatus(projectId, poll);
  const displayStatus = live?.status ?? status;
  const displayChunks = live?.chunksTotal ?? chunkCount;
  const displayEmbedded = live?.embedded ?? 0;
  const displayError = live?.errorMessage ?? errorMessage;

  const statusLabel = (() => {
    switch (displayStatus) {
      case "processed":
        return "Ready";
      case "processing":
        return `Processing · embedding ${displayEmbedded} of ${displayChunks}`;
      case "uploaded":
        return "Queued";
      case "failed":
        return displayError ? `Failed: ${displayError}` : "Failed";
      default:
        return displayStatus;
    }
  })();

  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium" title={filename}>
            {filename}
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground tabular">
            <span className="uppercase tracking-wide">{kind}</span>
            <span aria-hidden="true">·</span>
            <span>
              {displayChunks} {displayChunks === 1 ? "chunk" : "chunks"}
            </span>

            <SourceStatusBadge status={displayStatus} />
            {displayStatus === "processing" && (
              <span>
                embedding {displayEmbedded}/{displayChunks}
              </span>
            )}
            {displayError && displayStatus === "failed" && (
              <span className="text-destructive">{displayError}</span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="sr-only">{statusLabel}</span>
        <Button
          size="icon"
          variant="ghost"
          onClick={onDelete}
          aria-label={`Delete ${filename}`}
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
