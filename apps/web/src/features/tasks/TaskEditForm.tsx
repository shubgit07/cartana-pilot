"use client";

import * as React from "react";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RequirementSelect } from "./RequirementSelect";

const MAX_TITLE = 240;
const MAX_DESCRIPTION = 4000;

type Option = { id: string; title: string };

type Props = {
  initialTitle: string;
  initialDescription: string | null;
  initialRequirementId: string | null;
  linkableRequirements: Option[];
  saving: boolean;
  onSave: (patch: {
    title?: string;
    description?: string | null;
    requirementId?: string | null;
  }) => Promise<void>;
  onCancel: () => void;
};

export function TaskEditForm(props: Props) {
  const [title, setTitle] = React.useState(props.initialTitle);
  const [description, setDescription] = React.useState(props.initialDescription ?? "");
  const [requirementId, setRequirementId] = React.useState(props.initialRequirementId ?? "");
  const titleRef = React.useRef<HTMLInputElement | null>(null);
  React.useEffect(() => {
    titleRef.current?.focus();
    titleRef.current?.select();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await props.onSave({
      title: title.trim(),
      description: description.trim() || null,
      requirementId: requirementId || null,
    });
  }

  const titleError = title.trim().length === 0 ? "Title cannot be empty" : null;

  return (
    <form onSubmit={handleSubmit} className="space-y-3" noValidate>
      <div className="space-y-2">
        <Label htmlFor="task-edit-title">Title</Label>
        <Input
          id="task-edit-title"
          ref={titleRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={MAX_TITLE}
          autoComplete="off"
          spellCheck
          aria-invalid={titleError ? true : undefined}
          aria-describedby={titleError ? "task-edit-title-error" : undefined}
        />
        {titleError && (
          <p id="task-edit-title-error" role="alert" className="text-xs text-destructive">
            {titleError}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="task-edit-desc">Description</Label>
        <Textarea
          id="task-edit-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          maxLength={MAX_DESCRIPTION}
          placeholder="Optional context…"
        />
      </div>
      <RequirementSelect
        value={requirementId}
        onChange={setRequirementId}
        requirements={props.linkableRequirements}
        id="task-edit-requirement"
        name="taskEditRequirement"
      />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={props.onCancel} disabled={props.saving}>
          Cancel
        </Button>
        <Button type="submit" disabled={props.saving || !title.trim()}>
          {props.saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Save className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span className="ml-1.5">{props.saving ? "Saving…" : "Save"}</span>
        </Button>
      </div>
    </form>
  );
}
