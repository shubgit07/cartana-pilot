"use client";

import * as React from "react";
import { Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { projectsApi, ApiError } from "@/lib/api";

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
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="ml-1.5">Delete project</span>
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
