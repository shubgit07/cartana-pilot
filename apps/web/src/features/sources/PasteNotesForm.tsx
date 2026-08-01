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
import { useSources } from "@/hooks/api";
import { messageOf } from "@/hooks/api";

const DEFAULT_FILENAME = "notes.txt";

type Props = {
  projectId: string;
  busy: boolean;
  onBusyChange: (next: boolean) => void;
  onUploaded?: () => void;
};

export function PasteNotesForm({ projectId, busy, onBusyChange, onUploaded }: Props) {
  const [open, setOpen] = React.useState(false);
  const [filename, setFilename] = React.useState(DEFAULT_FILENAME);
  const [content, setContent] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const { createFromText } = useSources(projectId);
  const { toast } = useToast();

  const dirty = open && (filename !== DEFAULT_FILENAME || content.trim().length > 0);
  useUnsavedChanges(dirty);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleanFilename = filename.trim();
    const cleanContent = content.trim();
    if (!cleanFilename || !cleanContent) return;
    setSubmitting(true);
    onBusyChange(true);
    try {
      await createFromText(cleanFilename, cleanContent);
      onUploaded?.();
      setContent("");
      setFilename(DEFAULT_FILENAME);
      setOpen(false);

      toast({ title: "Source added", description: `${cleanFilename} is processing…` });
    } catch (err: unknown) {
      toast({
        title: "Could not add source",
        description: messageOf(err) ?? "Try again",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
      onBusyChange(false);
    }
  }

  if (!open) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Paste notes</CardTitle>
          <CardDescription>
            Already have text in a doc? Paste it in to skip uploading a file.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(true)}
            disabled={busy}
          >
            Open paste notes
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Paste notes</CardTitle>
        <CardDescription>Give it a name and paste the content.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          <div className="space-y-2">
            <Label htmlFor="paste-filename">
              Filename <span className="text-destructive" aria-hidden="true">*</span>
            </Label>
            <Input
              id="paste-filename"
              name="pasteFilename"
              autoComplete="off"
              spellCheck={false}
              placeholder="e.g. kickoff-notes.txt"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              required
              maxLength={200}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="paste-content">
              Content <span className="text-destructive" aria-hidden="true">*</span>
            </Label>
            <Textarea
              id="paste-content"
              name="pasteContent"
              rows={8}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              maxLength={200_000}
              placeholder="Paste a brief, meeting notes, requirements document…"
              required
            />
            <p className="text-xs text-muted-foreground tabular">{content.length}/200,000</p>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setOpen(false);
                setFilename(DEFAULT_FILENAME);
                setContent("");
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
            <SubmitButton
              type="submit"
              loading={submitting}
              loadingLabel="Adding…"
              disabled={!filename.trim() || !content.trim()}
            >
              Add source
            </SubmitButton>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
