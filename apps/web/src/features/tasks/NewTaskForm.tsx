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

  return (
    <Card>
      <CardHeader>
        <CardTitle>New task</CardTitle>
        <CardDescription>
          Add a task manually. Optionally link it to an existing requirement.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          <div className="space-y-2">
            <Label htmlFor="task-title">
              Title <span className="text-destructive" aria-hidden="true">*</span>
            </Label>
            <Input
              id="task-title"
              ref={titleRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Build OTP login flow…"
              maxLength={MAX_TITLE}
              autoComplete="off"
              spellCheck
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="task-desc">Description</Label>
            <Textarea
              id="task-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={MAX_DESCRIPTION}
              placeholder="Optional details…"
            />
          </div>
          <RequirementSelect
            value={requirementId}
            onChange={setRequirementId}
            requirements={linkableRequirements}
            id="task-requirement"
            name="taskRequirement"
          />
          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                reset();
                onOpenChange(false);
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
            <SubmitButton
              type="submit"
              loading={submitting}
              loadingLabel="Creating…"
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
