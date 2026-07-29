"use client";

import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { useToast } from "@/components/ui/toast";
import { messageOf, useRequirements, useTasks } from "@/hooks/api";
import { TasksHeader } from "./TasksHeader";
import { NewTaskForm } from "./NewTaskForm";
import { TaskRow } from "./TaskRow";
import type { TaskSummary } from "@cartana/shared";

type Props = { projectId: string };

export function TasksPanel({ projectId }: Props) {
  const { tasks, loading, error, reload, update, remove } = useTasks(projectId);
  const { requirements } = useRequirements(projectId);
  const { toast } = useToast();
  const [creating, setCreating] = React.useState(false);
  const [pendingDelete, setPendingDelete] = React.useState<TaskSummary | null>(null);

  const linkable = (requirements ?? []).filter((r) => r.state !== "rejected");
  const linkableOptions = React.useMemo(
    () => linkable.map((r) => ({ id: r.id, title: r.title })),
    [linkable]
  );

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
    t: TaskSummary,
    patch: { title?: string; description?: string | null; requirementId?: string | null }
  ) {
    try {
      await update(t.id, patch);
      toast({ title: "Task updated" });
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
      toast({ title: "Task deleted" });
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
    <div className="space-y-4">
      <TasksHeader
        creating={creating}
        busy={loading}
        onToggleCreate={() => setCreating((c) => !c)}
        onRefresh={reload}
      />

      {/* Persistent wrapper so TasksHeader's aria-controls always resolves. */}
      <div id="new-task-card">
        {creating && (
          <NewTaskForm
            projectId={projectId}
            open={creating}
            onOpenChange={setCreating}
            linkableRequirements={linkableOptions}
          />
        )}
      </div>

      <Card>
        <CardContent className="pt-5">
          {loading && (
            <div className="space-y-2" aria-busy="true" aria-label="Loading tasks">
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

          {!loading && tasks && tasks.length === 0 && (
            <EmptyState
              icon="inbox"
              title="No tasks yet"
              description="Extracted tasks appear after a document is processed, or create one manually."
            />
          )}

          {!loading && tasks && tasks.length > 0 && (
            <ul className="space-y-2">
              {tasks.map((t) => (
                <li key={t.id}>
                  <TaskRow
                    task={t}
                    linkableRequirements={linkableOptions}
                    onAccept={() => setState(t.id, "accepted")}
                    onReject={() => setState(t.id, "rejected")}
                    onSave={(patch) => handleSave(t, patch)}
                    onDelete={() => setPendingDelete(t)}
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
        title={pendingDelete ? `Delete "${pendingDelete.title}"?` : ""}
        description="This removes the task. This action can't be undone."
        confirmLabel="Delete task"
        cancelLabel="Keep task"
        destructive
        onConfirm={handleDelete}
      />
    </div>
  );
}
