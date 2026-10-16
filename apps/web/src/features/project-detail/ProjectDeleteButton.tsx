"use client";

import * as React from "react";
import { Loader2, Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { projectsApi, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";

type Props = {
  projectId: string;
  projectName: string;
  onDeleted: () => void;
};

export function ProjectDeleteButton({ projectId, projectName, onDeleted }: Props) {
  const [open, setOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const { toast } = useToast();

  async function handle() {
    setBusy(true);
    try {
      await projectsApi.remove(projectId);
      toast({ title: "Project deleted", description: projectName });
      onDeleted();
    } catch (e: unknown) {
      toast({
        title: "Delete failed",
        description: e instanceof ApiError ? e.message : "Try again",
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        disabled={busy}
        className={cn(
          "shrink-0 transition-colors duration-200 ease-out-expo",
          "hover:border-danger/40 hover:bg-danger-soft hover:text-danger-soft-foreground",
          "focus-visible:ring-danger"
        )}
      >
        {busy ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        ) : (
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        <span className="ml-1.5 hidden sm:inline">Delete project</span>
        <span className="ml-1.5 sm:hidden">Delete</span>
      </Button>

      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Delete "${projectName}"?`}
        description="This removes the project and all of its sources, chunks, and embeddings. This action can't be undone."
        confirmLabel="Delete project"
        cancelLabel="Keep project"
        destructive
        loading={busy}
        onConfirm={handle}
      />
    </>
  );
}
