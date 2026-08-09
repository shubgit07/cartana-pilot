"use client";

import * as React from "react";
import { Files, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { useToast } from "@/components/ui/toast";
import { messageOf, useSources } from "@/hooks/api";
import { SourcesHeader } from "./SourcesHeader";
import { SourceRow } from "./SourceRow";
import { UploadFileCard } from "./UploadFileCard";
import { PasteNotesForm } from "./PasteNotesForm";
import { PasteDiffForm } from "./PasteDiffForm";

type Props = {
  projectId: string;
  onSourceCountChange?: (count: number) => void;
};

export function SourcesPanel({ projectId, onSourceCountChange }: Props) {
  const { sources, loading, error, reload, remove } = useSources(projectId);
  const { toast } = useToast();
  const [showPaste, setShowPaste] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [pendingDelete, setPendingDelete] = React.useState<{
    id: string;
    name: string;
  } | null>(null);

  React.useEffect(() => {
    if (sources !== null) {
      onSourceCountChange?.(sources.length);
    }
  }, [sources, onSourceCountChange]);


  async function handleDelete() {
    if (!pendingDelete) return;
    try {
      await remove(pendingDelete.id);
      toast({
        title: "Source deleted",
        description: pendingDelete.name,
      });
    } catch (e: unknown) {
      toast({
        title: "Delete failed",
        description: messageOf(e) ?? "Try again",
        variant: "destructive",
      });
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div className="space-y-6">
      <SourcesHeader
        showPaste={showPaste}
        onShowPasteChange={setShowPaste}
        busy={busy}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <UploadFileCard projectId={projectId} busy={busy} onBusyChange={setBusy} onUploaded={reload} />
        <PasteDiffForm projectId={projectId} busy={busy} onBusyChange={setBusy} onUploaded={reload} />
      </div>

      <div id="paste-notes-card">
        {showPaste && (
          <PasteNotesForm projectId={projectId} busy={busy} onBusyChange={setBusy} onUploaded={reload} />
        )}
      </div>


      <Card>
        <CardHeader className="gap-3 border-b border-border/70">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Library</span>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Files className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Sources
              </CardTitle>
              <CardDescription>
                Status updates automatically. Refresh after uploads complete.
              </CardDescription>
            </div>

            <Button size="sm" variant="outline" onClick={reload} className="shrink-0">
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="ml-1.5">Refresh</span>
            </Button>
          </div>
        </CardHeader>

        <CardContent className="pt-5">
          {loading && (
            <div className="space-y-2" aria-busy="true" aria-label="Loading sources">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p
              role="alert"
              className="rounded-lg border border-danger/25 bg-danger-soft px-3 py-2 text-sm text-danger-soft-foreground"
            >
              {error}
            </p>
          )}
          {!loading && sources && sources.length === 0 && (
            <EmptyState
              icon="inbox"
              title="No sources yet"
              description="Upload a brief or paste notes to get started."
            />
          )}
          {!loading && sources && sources.length > 0 && (
            <ul className="space-y-2">
              {sources.map((s) => (
                <li key={s.id}>
                  <SourceRow
                    projectId={projectId}
                    sourceId={s.id}
                    filename={s.filename}
                    kind={s.kind}
                    status={s.status}
                    chunkCount={s.chunkCount}
                    errorMessage={s.errorMessage}
                    onDelete={() => setPendingDelete({ id: s.id, name: s.filename })}
                  />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!pendingDelete}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title={pendingDelete ? `Delete "${pendingDelete.name}"?` : ""}
        description="This removes the source and all of its chunks and embeddings. This action can't be undone."
        confirmLabel="Delete source"
        cancelLabel="Keep source"
        destructive
        onConfirm={handleDelete}
      />
    </div>
  );
}
