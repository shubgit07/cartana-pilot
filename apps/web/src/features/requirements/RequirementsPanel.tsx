"use client";

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import {
  ChevronDown,
  FileText,
  ListChecks,
  Plus,
  RefreshCw,
  Upload,
} from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { messageOf, useRequirements, useSources } from "@/hooks/api";
import { RequirementRow } from "./RequirementRow";
import { UploadFileCard } from "../sources/UploadFileCard";
import { PasteNotesForm } from "../sources/PasteNotesForm";
import { SourceStatusBadge } from "../sources/SourceStatusBadge";
import type { RequirementSummary } from "@cartana/shared";

type Props = { projectId: string };

export function RequirementsPanel({ projectId }: Props) {
  const { requirements, loading, error, update, remove, reload } = useRequirements(projectId);
  const { sources, reload: reloadSources } = useSources(projectId);
  const { toast } = useToast();

  const [pendingDelete, setPendingDelete] = React.useState<RequirementSummary | null>(null);
  const [showImport, setShowImport] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  const acceptedCount = requirements?.filter((r) => r.state === "accepted").length ?? 0;
  const totalCount = requirements?.length ?? 0;
  const sourceCount = sources?.length ?? 0;

  const handleAllReload = React.useCallback(async () => {
    await Promise.all([reload(), reloadSources()]);
  }, [reload, reloadSources]);

  async function setState(id: string, state: "accepted" | "rejected") {
    try {
      await update(id, { state });
    } catch (e: unknown) {
      toast({
        title: "Update failed",
        description: messageOf(e) ?? "Try again",
        variant: "destructive",
      });
    }
  }

  async function handleSave(
    r: RequirementSummary,
    patch: { title?: string; description?: string | null }
  ) {
    try {
      await update(r.id, patch);
      toast({ title: "Requirement updated" });
    } catch (e: unknown) {
      toast({
        title: "Update failed",
        description: messageOf(e) ?? "Try again",
        variant: "destructive",
      });
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    try {
      await remove(pendingDelete.id);
      toast({ title: "Requirement deleted" });
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
      {/* Spec & Source Ingestion Section */}
      <Card className="border-border/80 bg-surface">
        <CardHeader className="gap-3 border-b border-border/70 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Source Material</span>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Spec & Document Ingestion
              </CardTitle>
              <CardDescription>
                Upload PRDs, markdown briefs, or paste specification text to extract traceable requirements.
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={showImport ? "secondary" : "default"}
                onClick={() => setShowImport((v) => !v)}
              >
                {showImport ? (
                  <>
                    <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="ml-1.5">Collapse Import</span>
                  </>
                ) : (
                  <>
                    <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="ml-1.5">Import Document / Spec</span>
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Active Sources Badges Strip */}
          {sources && sources.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                Ingested Material ({sourceCount}):
              </span>
              {sources.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center gap-1.5 rounded-md border border-border/60 bg-surface-sunken px-2 py-1 text-xs"
                >
                  <span className="font-mono text-xs text-foreground truncate max-w-[180px]">
                    {s.filename}
                  </span>
                  <SourceStatusBadge status={s.status} />
                  <span className="text-2xs text-muted-foreground tabular">
                    ({s.chunkCount} chunks)
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardHeader>

        {showImport && (
          <CardContent className="animate-fade-in space-y-4 pt-4 border-b border-border/70 bg-surface-sunken/40">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <UploadFileCard
                projectId={projectId}
                busy={busy}
                onBusyChange={setBusy}
                onUploaded={handleAllReload}
              />
              <PasteNotesForm
                projectId={projectId}
                busy={busy}
                onBusyChange={setBusy}
                onUploaded={handleAllReload}
              />
            </div>
          </CardContent>
        )}
      </Card>

      {/* Extracted Requirements List */}
      <Card>
        <CardHeader className="gap-3 border-b border-border/70">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Scope</span>
              <CardTitle className="flex items-center gap-2 text-lg">
                <ListChecks className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Requirements
              </CardTitle>
              <CardDescription>
                Extracted from your project material. Accept, edit, or reject each suggestion.
              </CardDescription>
            </div>

            <div className="flex shrink-0 items-center gap-3">
              {totalCount > 0 && (
                <span className="text-xs text-muted-foreground tabular">
                  {acceptedCount}/{totalCount} accepted
                </span>
              )}
              <Button size="sm" variant="outline" onClick={handleAllReload}>
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="ml-1.5">Refresh</span>
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-5">
          {loading && (
            <div className="space-y-2" aria-busy="true" aria-label="Loading requirements">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
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

          {!loading && requirements && requirements.length === 0 && (
            <div className="py-6">
              <EmptyState
                icon="inbox"
                title="No requirements yet"
                description="Upload a PRD document or paste spec notes above to automatically extract traceable requirements."
                actions={
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowImport(true)}
                    className="mt-2"
                  >
                    <Upload className="mr-1.5 h-3.5 w-3.5" />
                    Open Document Importer
                  </Button>
                }
              />
            </div>
          )}

          {!loading && requirements && requirements.length > 0 && (
            <ul className="space-y-2">
              {requirements.map((r) => (
                <li key={r.id}>
                  <RequirementRow
                    requirement={r}
                    onAccept={() => setState(r.id, "accepted")}
                    onReject={() => setState(r.id, "rejected")}
                    onSave={(patch) => handleSave(r, patch)}
                    onDelete={() => setPendingDelete(r)}
                  />
                </li>
              ))}
            </ul>
          )}
        </CardContent>

        <ConfirmDialog
          open={!!pendingDelete}
          onOpenChange={(o) => !o && setPendingDelete(null)}
          title={pendingDelete ? `Delete "${pendingDelete.title}"?` : ""}
          description="This removes the requirement. This action can't be undone."
          confirmLabel="Delete requirement"
          cancelLabel="Keep requirement"
          destructive
          onConfirm={handleDelete}
        />
      </Card>
    </div>
  );
}
