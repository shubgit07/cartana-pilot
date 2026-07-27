"use client";

import * as React from "react";
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

type Props = { projectId: string };

export function SourcesPanel({ projectId }: Props) {
  const { sources, loading, error, reload, remove } = useSources(projectId);
  const { toast } = useToast();
  const [showPaste, setShowPaste] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [pendingDelete, setPendingDelete] = React.useState<{
    id: string;
    name: string;
  } | null>(null);

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
        action="both"
        showPaste={showPaste}
        onShowPasteChange={setShowPaste}
        busy={busy}
      />

      <UploadFileCard projectId={projectId} busy={busy} onBusyChange={setBusy} />
      <div id="paste-notes-card">
        {showPaste && (
          <PasteNotesForm projectId={projectId} busy={busy} onBusyChange={setBusy} />
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Sources</CardTitle>
            <CardDescription>
              Status updates automatically. Refresh after uploads complete.
            </CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={reload}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
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
            <ul className="divide-y">
              {sources.map((s) => (
                <li key={s.id} className="py-3 first:pt-0 last:pb-0">
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
