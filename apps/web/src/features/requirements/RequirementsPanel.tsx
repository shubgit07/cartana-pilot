"use client";

import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { ListChecks } from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { messageOf, useRequirements } from "@/hooks/api";
import { RequirementRow } from "./RequirementRow";
import type { RequirementSummary } from "@cartana/shared";

type Props = { projectId: string };

export function RequirementsPanel({ projectId }: Props) {
  const { requirements, loading, error, update, remove, reload } = useRequirements(projectId);
  const { toast } = useToast();
  const [pendingDelete, setPendingDelete] = React.useState<RequirementSummary | null>(null);

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
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <ListChecks className="h-4 w-4" aria-hidden="true" />
            Requirements
          </CardTitle>
          <CardDescription>
            Extracted from your project material. Accept, edit, or reject each suggestion.
          </CardDescription>
        </div>
        <Button size="sm" variant="outline" onClick={reload}>
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="space-y-3" aria-busy="true">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        )}
        {error && (
          <p role="alert" className="text-sm text-destructive">
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
          <ul className="divide-y">
            {requirements.map((r) => (
              <li key={r.id} className="py-4 first:pt-0 last:pb-0">
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
