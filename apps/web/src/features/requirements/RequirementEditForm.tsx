"use client";

import * as React from "react";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

const MAX_TITLE = 240;
const MAX_DESCRIPTION = 4000;

export function RequirementEditForm({
  initialTitle,
  initialDescription,
  saving,
  onSave,
  onCancel,
}: {
  initialTitle: string;
  initialDescription: string | null;
  saving: boolean;
  onSave: (patch: { title: string; description: string | null }) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle] = React.useState(initialTitle);
  const [description, setDescription] = React.useState(initialDescription ?? "");
  const titleInputRef = React.useRef<HTMLInputElement | null>(null);

  React.useEffect(() => {
    titleInputRef.current?.focus();
    titleInputRef.current?.select();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await onSave({
      title: title.trim(),
      description: description.trim() || null,
    });
  }

  const titleError =
    title.trim().length === 0 ? "Title cannot be empty" : title.length === MAX_TITLE ? "Title is at the maximum length" : null;

  return (
    <form onSubmit={handleSubmit} className="space-y-3" noValidate>
      <div className="space-y-2">
        <Label htmlFor="req-edit-title">Title</Label>
        <Input
          id="req-edit-title"
          ref={titleInputRef}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={MAX_TITLE}
          autoComplete="off"
          spellCheck
          aria-invalid={titleError ? true : undefined}
          aria-describedby={titleError ? "req-edit-title-error" : undefined}
        />
        {titleError && (
          <p id="req-edit-title-error" role="alert" className="text-xs text-destructive">
            {titleError}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="req-edit-desc">Description</Label>
        <Textarea
          id="req-edit-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          maxLength={MAX_DESCRIPTION}
          placeholder="Optional context…"
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !title.trim()}>
          {saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Save className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span className="ml-1.5">{saving ? "Saving…" : "Save"}</span>
        </Button>
      </div>
    </form>
  );
}
