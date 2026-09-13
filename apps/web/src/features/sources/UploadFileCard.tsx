"use client";

import * as React from "react";
import { CheckCircle2, Loader2, Upload, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { SourceFileInput } from "@/components/common/SourceFileInput";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { useSourceStatus, useSources } from "@/hooks/api";
import { messageOf } from "@/hooks/api";
import { cn } from "@/lib/cn";
import type { SourceSummary } from "@cartana/shared";

type Props = {
  projectId: string;
  busy: boolean;
  onBusyChange: (next: boolean) => void;
  onUploaded?: (source: SourceSummary) => void;
};

/** Rotating copy shown while the pipeline runs — keeps the wait feeling alive. */
const ENGAGEMENT_COPY = [
  "Reading your document…",
  "Hunting for requirements…",
  "Chunking for context…",
  "Connecting the dots…",
  "Almost there…",
];
const COPY_INTERVAL_MS = 2600;

type Phase = "idle" | "working" | "done" | "failed";

export function UploadFileCard({ projectId, busy, onBusyChange, onUploaded }: Props) {
  const { uploadFile } = useSources(projectId);
  const { toast } = useToast();
  const [sourceId, setSourceId] = React.useState<string | null>(null);
  const [copyIndex, setCopyIndex] = React.useState(0);

  const live = useSourceStatus(projectId, sourceId);

  React.useEffect(() => {
    setSourceId(null);
    setCopyIndex(0);
  }, [projectId]);

  const phase: Phase =
    sourceId === null || live === null
      ? sourceId === null
        ? "idle"
        : "working"
      : live.status === "failed"
        ? "failed"
        : live.status === "processed"
          ? "done"
          : "working";

  const stage = live?.stage ?? "uploading";

  React.useEffect(() => {
    if (phase !== "working") return;
    const timer = window.setInterval(() => {
      setCopyIndex((i) => (i + 1) % ENGAGEMENT_COPY.length);
    }, COPY_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [phase]);

  const progressPct = (() => {
    if (phase === "done" || phase === "failed") return 100;
    if (stage === "chunking" && live && live.chunksTotal > 0) {
      return Math.round(30 + (live.embedded / live.chunksTotal) * 40);
    }
    return 20;
  })();

  const pillLabel =
    phase === "working"
      ? stage === "chunking"
        ? "Chunking…"
        : "Uploading…"
      : phase === "done"
        ? "Ready"
        : phase === "failed"
          ? "Upload failed"
          : "Upload";

  async function handle(file: File) {
    onBusyChange(true);
    try {
      const source = await uploadFile(file);
      setSourceId(source.id);
      setCopyIndex(0);
      onUploaded?.(source);
      toast({ title: "Upload started", description: `${file.name} is processing…` });
    } catch (e: unknown) {
      toast({
        title: "Upload failed",
        description: messageOf(e) ?? "Try again",
        variant: "destructive",
      });
    } finally {
      onBusyChange(false);
    }
  }

  return (
    <Card>
      <CardHeader className="gap-1.5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
          >
            <Upload className="h-4 w-4" />
          </span>
          <span className="eyebrow">Upload</span>
        </div>
        <CardTitle className="text-base">Upload a file</CardTitle>
        <CardDescription className="leading-relaxed">
          PDF or plain text (≤ a few MB). Larger files upload in chunks.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {phase === "idle" && (
          <>
            <SourceFileInput onFile={handle} disabled={busy} loading={busy} />
            <p className="mt-3 text-2xs leading-relaxed text-muted-foreground">
              Files are chunked and embedded automatically — no extra step needed.
              Requirements are extracted automatically and listed below.
            </p>
          </>
        )}

        {phase !== "idle" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <span
                role="status"
                aria-live="polite"
                className={cn(
                  "inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium",
                  phase === "working" && "border-border bg-surface",
                  phase === "done" &&
                    "border-success/30 bg-success-soft text-success-soft-foreground",
                  phase === "failed" &&
                    "border-danger/30 bg-danger-soft text-danger-soft-foreground"
                )}
              >
                {phase === "working" ? (
                  <Loader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                ) : phase === "done" ? (
                  <CheckCircle2 className="size-4" aria-hidden="true" />
                ) : (
                  <XCircle className="size-4" aria-hidden="true" />
                )}
                {pillLabel}
              </span>

              {(phase === "done" || phase === "failed") && (
                <Button size="sm" variant="outline" onClick={() => setSourceId(null)}>
                  <Upload className="h-3.5 w-3.5" aria-hidden="true" />
                  <span className="ml-1.5">Upload another</span>
                </Button>
              )}
            </div>

            <div
              role="progressbar"
              aria-label="Upload progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPct}
              className="h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken"
            >
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-300 ease-out-expo",
                  phase === "failed" ? "bg-danger" : "bg-primary"
                )}
                style={{ width: `${progressPct}%` }}
              />
            </div>

            <p aria-live="polite" className="text-xs leading-relaxed text-muted-foreground">
              {phase === "working" && ENGAGEMENT_COPY[copyIndex]}
              {phase === "done" &&
                "Requirements extracted — they're ready in the Requirements tab."}
              {phase === "failed" && (live?.errorMessage ?? "Something went wrong. Try again.")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
