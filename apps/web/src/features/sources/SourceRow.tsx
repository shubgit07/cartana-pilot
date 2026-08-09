"use client";

import * as React from "react";
import { FileText, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SourceStatusBadge } from "./SourceStatusBadge";
import { useSourceStatus } from "@/hooks/api";
import { cn } from "@/lib/cn";

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
  const displayStage = live?.stage ?? null;

  const statusLabel = (() => {
    switch (displayStatus) {
      case "processed":
        return "Ready";
      case "processing":
        return displayStage === "chunking"
          ? "Processing · chunking and embedding"
          : "Processing · reading and chunking";
      case "uploaded":
        return "Queued";
      case "failed":
        return displayError ? `Failed: ${displayError}` : "Failed";
      default:
        return displayStatus;
    }
  })();

  /** Embedding progress as a whole percentage, shown only while processing. */
  const progressPct =
    displayStatus === "processing" && displayChunks > 0
      ? Math.min(100, Math.round((displayEmbedded / displayChunks) * 100))
      : null;

  return (
    <div
      className={cn(
        "group relative flex items-center justify-between gap-4",
        "rounded-lg border border-border/70 bg-surface py-3 pl-3.5 pr-3",
        "transition-[border-color,box-shadow] duration-200 ease-out-expo",
        "hover:border-border-strong hover:shadow-card",
        displayStatus === "failed" && "border-danger/25"
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span
          aria-hidden="true"
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-md border border-border/70 bg-surface-sunken text-muted-foreground"
        >
          <FileText className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium leading-snug" title={filename}>
            {filename}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground tabular">
            <span className="rounded border border-border/70 bg-surface-sunken px-1 py-px text-2xs font-medium uppercase tracking-wide">
              {kind}
            </span>
            <span>
              {displayChunks} {displayChunks === 1 ? "chunk" : "chunks"}
            </span>

            <SourceStatusBadge status={displayStatus} />
            {displayStatus === "processing" && (
              <span aria-live="polite">
                {displayEmbedded > 0
                  ? `embedding ${displayEmbedded}/${displayChunks}`
                  : displayStage === "chunking"
                    ? "chunking"
                    : "reading file"}
              </span>
            )}
            {displayError && displayStatus === "failed" && (
              <span className="text-danger">{displayError}</span>
            )}
          </div>

          {progressPct !== null && (
            <div
              role="progressbar"
              aria-label={`Embedding ${filename}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPct}
              className="mt-2 h-1 w-full max-w-xs overflow-hidden rounded-full bg-surface-sunken"
            >
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out-expo"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="sr-only">{statusLabel}</span>
        <Button
          size="icon"
          variant="ghost"
          onClick={onDelete}
          aria-label={`Delete ${filename}`}
          className="text-muted-foreground transition-colors hover:text-danger"
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
