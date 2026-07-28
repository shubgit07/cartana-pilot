"use client";

import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { ListChecks, RefreshCw } from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { messageOf, useRequirements } from "@/hooks/api";
import { RequirementRow } from "./RequirementRow";
import type { RequirementSummary } from "@cartana/shared";

type Props = { projectId: string };

export function RequirementsPanel({ projectId }: Props) {
  const { requirements, loading, error, update, remove, reload } = useRequirements(projectId);
  const { toast } = useToast();
  const [pendingDelete, setPendingDelete] = React.useState<RequirementSummary | null>(null);

  const acceptedCount = requirements?.filter((r) => r.state === "accepted").length ?? 0;
  const totalCount = requirements?.length ?? 0;

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

  async function handleSave(r: RequirementSummary, patch: { title?: string; description?: string | null }) {
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
            <Button size="sm" variant="outline" onClick={reload}>
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
          <EmptyState
            icon="inbox"
            title="No requirements yet"
            description="Once you upload a document, extraction will start automatically."
          />
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
  );
}
