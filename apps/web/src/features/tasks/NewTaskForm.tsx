"use client";

import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SubmitButton } from "@/components/common/SubmitButton";
import { useToast } from "@/components/ui/toast";
import { useUnsavedChanges } from "@/hooks/common";
import { useTasks } from "@/hooks/api";
import { messageOf } from "@/hooks/api";
import { RequirementSelect } from "./RequirementSelect";

const MAX_TITLE = 240;
const MAX_DESCRIPTION = 4000;

/** Show the counter only once the value is close to the cap. */
const COUNTER_THRESHOLD = 0.8;

type Option = { id: string; title: string };

type Props = {
  projectId: string;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  linkableRequirements: Option[];
};

export function NewTaskForm({ projectId, open, onOpenChange, linkableRequirements }: Props) {
  const { create } = useTasks(projectId);
  const { toast } = useToast();
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [requirementId, setRequirementId] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const titleRef = React.useRef<HTMLInputElement | null>(null);

  // Scoped ids avoid colliding with the inline task edit form.
  const uid = React.useId();
  const titleId = `${uid}-title`;
  const descId = `${uid}-desc`;
  const reqId = `${uid}-requirement`;

  const dirty =
    open && (title.trim().length > 0 || description.trim().length > 0 || !!requirementId);
  useUnsavedChanges(dirty);

  React.useEffect(() => {
    if (open) {
      // Defer until after layout
      const t = window.setTimeout(() => titleRef.current?.focus(), 0);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [open]);

  function reset() {
    setTitle("");
    setDescription("");
    setRequirementId("");
  }

  function handleCancel() {
    reset();
    onOpenChange(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape" && !submitting) {
      e.preventDefault();
      handleCancel();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      titleRef.current?.focus();
      return;
    }
    setSubmitting(true);
    try {
      await create({
        title: title.trim(),
        description: description.trim() || null,
        requirementId: requirementId || null,
      });
      reset();
      onOpenChange(false);
      toast({ title: "Task created" });
    } catch (err: unknown) {
      toast({
        title: "Create failed",
        description: messageOf(err) ?? "Try again",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  const showTitleCount = title.length >= MAX_TITLE * COUNTER_THRESHOLD;
  const showDescCount = description.length >= MAX_DESCRIPTION * COUNTER_THRESHOLD;

  return (
    // id is referenced by TasksHeader's aria-controls.
    <Card id="new-task-card" className="animate-scale-in border-primary/25">
      <CardHeader className="gap-1 border-b border-border/70">
        <span className="eyebrow">Create</span>
        <CardTitle className="text-lg">New task</CardTitle>
        <CardDescription>
          Add a task manually. Optionally link it to an existing requirement.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-5">
        <form onSubmit={handleSubmit} onKeyDown={handleKeyDown} className="space-y-3" noValidate>
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <Label htmlFor={titleId}>
                Title{" "}
                <span className="text-danger" aria-hidden="true">
                  *
                </span>
              </Label>
              {showTitleCount && (
                <span className="text-2xs text-muted-foreground tabular">
                  {title.length}/{MAX_TITLE}
                </span>
              )}
            </div>
            <Input
              id={titleId}
              ref={titleRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Build OTP login flow\u2026"
              maxLength={MAX_TITLE}
              autoComplete="off"
              spellCheck
              required
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <Label htmlFor={descId}>Description</Label>
              {showDescCount && (
                <span className="text-2xs text-muted-foreground tabular">
                  {description.length}/{MAX_DESCRIPTION}
                </span>
              )}
            </div>
            <Textarea
              id={descId}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={MAX_DESCRIPTION}
              placeholder="Optional details\u2026"
            />
          </div>

          <RequirementSelect
            value={requirementId}
            onChange={setRequirementId}
            requirements={linkableRequirements}
            id={reqId}
            name="taskRequirement"
          />

          <div className="flex items-center justify-end gap-2 border-t border-border/70 pt-3">
            <span className="mr-auto hidden text-2xs text-muted-foreground sm:block">
              Press <kbd className="font-mono">Esc</kbd> to cancel
            </span>
            <Button type="button" variant="ghost" onClick={handleCancel} disabled={submitting}>
              Cancel
            </Button>
            <SubmitButton
              type="submit"
              loading={submitting}
              loadingLabel="Creating\u2026"
              disabled={!title.trim()}
            >
              Create task
            </SubmitButton>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
