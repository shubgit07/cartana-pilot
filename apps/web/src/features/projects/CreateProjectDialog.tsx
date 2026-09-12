"use client";

import * as React from "react";
import { Box } from "lucide-react";
import type { ProjectSummary } from "@cartana/shared";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SubmitButton } from "@/components/common/SubmitButton";
import { projectsApi, ApiError } from "@/lib/api";
import { VISUALLY_HIDDEN_CLASS } from "@/lib/aria";
import { cn } from "@/lib/cn";

const MAX_NAME = 120;
const MAX_SUMMARY = 280;
const MAX_DESCRIPTION = 2000;

/**
 * Linear-style floating project composer. Shape follows the export
 * (breadcrumb, icon, 24px editable title, summary, description area,
 * footer Create) but only ships fields our API supports — property rows
 * (status/priority/lead/…) and agent actions are omitted, not faked.
 */
export function CreateProjectDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onCreated: (project: ProjectSummary) => void;
}) {
  const [name, setName] = React.useState("");
  const [summary, setSummary] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [touched, setTouched] = React.useState(false);

  const nameError = touched && name.trim().length === 0 ? "Name is required" : null;

  const inputRef = React.useRef<HTMLInputElement | null>(null);

  // Fresh form every time the composer opens; focus the title.
  React.useEffect(() => {
    if (open) {
      setName("");
      setSummary("");
      setDescription("");
      setError(null);
      setTouched(false);
      setSubmitting(false);
      const t = window.setTimeout(() => inputRef.current?.focus(), 50);
      return () => window.clearTimeout(t);
    }
  }, [open ]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!name.trim()) {
      inputRef.current?.focus();
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const trimmedSummary = summary.trim();
      const trimmedDescription = description.trim();
      const combined = [trimmedSummary, trimmedDescription]
        .filter(Boolean)
        .join("\n\n");
      const project = await projectsApi.create({
        name: name.trim(),
        description: combined ? combined : null,
      });
      onCreated(project);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? e.message : "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl gap-0 overflow-hidden p-0">
        <DialogTitle className={VISUALLY_HIDDEN_CLASS}>New project</DialogTitle>
        <DialogDescription className={VISUALLY_HIDDEN_CLASS}>
          Create a new project with a name and description.
        </DialogDescription>

        {/* Breadcrumb row */}
        <div className="flex items-center gap-1.5 border-b border-border px-5 py-3 text-[13px]">
          <span className="grid size-5 place-items-center rounded-md bg-primary text-primary-foreground">
            <Box className="size-3" aria-hidden="true" />
          </span>
          <span className="font-medium text-muted-foreground">Cartana</span>
          <span aria-hidden="true" className="text-muted-foreground">
            ›
          </span>
          <span className="font-medium text-foreground">New project</span>
        </div>

        <form onSubmit={onSubmit} noValidate>
          <div className="space-y-3 px-5 py-4">
            <Input
              ref={inputRef}
              id="composerName"
              name="composerName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Project name"
              aria-label="Project name"
              required
              maxLength={MAX_NAME}
              autoComplete="off"
              spellCheck={false}
              aria-invalid={nameError ? true : undefined}
              aria-describedby={nameError ? "composerName-error" : undefined}
              className={cn(
                "h-auto border-transparent bg-transparent px-0 text-2xl font-semibold tracking-tight shadow-none",
                "placeholder:text-muted-foreground/60 hover:border-transparent",
                "focus-visible:border-transparent focus-visible:ring-0",
                nameError && "placeholder:text-danger/60"
              )}
            />
            {nameError && (
              <p id="composerName-error" role="alert" className="-mt-1 text-xs text-danger">
                {nameError}
              </p>
            )}

            <Input
              id="composerSummary"
              name="composerSummary"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Add a short summary…"
              aria-label="Short summary"
              maxLength={MAX_SUMMARY}
              autoComplete="off"
              spellCheck
              className={cn(
                "h-auto border-transparent bg-transparent px-0 text-sm shadow-none",
                "placeholder:text-muted-foreground/60 hover:border-transparent",
                "focus-visible:border-transparent focus-visible:ring-0"
              )}
            />

            <Textarea
              id="composerDescription"
              name="composerDescription"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Write a description, a project brief, or collect ideas…"
              aria-label="Description"
              rows={5}
              maxLength={MAX_DESCRIPTION}
              spellCheck
              className={cn(
                "min-h-0 resize-none border-transparent bg-transparent px-0 shadow-none",
                "placeholder:text-muted-foreground/60 hover:border-transparent",
                "focus-visible:border-transparent focus-visible:ring-0"
              )}
            />

            {error && (
              <p
                role="alert"
                className="rounded-xl border border-danger/25 bg-danger-soft px-3 py-2 text-sm text-danger-soft-foreground"
              >
                {error}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-3">
            <span className="text-xs text-muted-foreground tabular">
              {name.trim().length}/{MAX_NAME}
            </span>
            <div className="flex items-center gap-2">
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <SubmitButton loading={submitting} loadingLabel="Creating…">
                Create project
              </SubmitButton>
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
