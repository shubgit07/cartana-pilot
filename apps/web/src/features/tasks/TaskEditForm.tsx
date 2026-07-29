"use client";

import * as React from "react";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RequirementSelect } from "./RequirementSelect";
import { cn } from "@/lib/cn";

const MAX_TITLE = 240;
const MAX_DESCRIPTION = 4000;

/** Show the counter only once the value is close to the cap. */
const COUNTER_THRESHOLD = 0.8;

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

  // Scoped ids keep label/error associations valid when several forms are open.
  const uid = React.useId();
  const titleId = `${uid}-title`;
  const titleErrorId = `${uid}-title-error`;
  const descId = `${uid}-desc`;
  const reqId = `${uid}-requirement`;

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

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      props.onCancel();
    }
  }

  const titleError = title.trim().length === 0 ? "Title cannot be empty" : null;

  const showTitleCount = title.length >= MAX_TITLE * COUNTER_THRESHOLD;
  const showDescCount = description.length >= MAX_DESCRIPTION * COUNTER_THRESHOLD;

  return (
    <form
      onSubmit={handleSubmit}
      onKeyDown={handleKeyDown}
      className="space-y-3 rounded-lg border border-border/70 bg-surface-sunken p-3"
      noValidate
    >
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between gap-2">
          <Label htmlFor={titleId}>Title</Label>
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
          maxLength={MAX_TITLE}
          autoComplete="off"
          spellCheck
          aria-invalid={titleError ? true : undefined}
          aria-describedby={titleError ? titleErrorId : undefined}
          className={cn(titleError && "border-danger focus-visible:ring-danger")}
        />
        {titleError && (
          <p id={titleErrorId} role="alert" className="text-xs text-danger">
            {titleError}
          </p>
        )}
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
          placeholder="Optional context\u2026"
        />
      </div>

      <RequirementSelect
        value={requirementId}
        onChange={setRequirementId}
        requirements={props.linkableRequirements}
        id={reqId}
        name="taskEditRequirement"
      />

      <div className="flex items-center justify-end gap-2 border-t border-border/70 pt-3">
        <span className="mr-auto hidden text-2xs text-muted-foreground sm:block">
          Press <kbd className="font-mono">Esc</kbd> to cancel
        </span>
        <Button type="button" variant="ghost" onClick={props.onCancel} disabled={props.saving}>
          Cancel
        </Button>
        <Button type="submit" disabled={props.saving || !title.trim()}>
          {props.saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Save className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span className="ml-1.5">{props.saving ? "Saving\u2026" : "Save"}</span>
        </Button>
      </div>
    </form>
  );
}
