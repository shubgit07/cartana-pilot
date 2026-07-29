"use client";

import * as React from "react";
import { ClipboardPaste } from "lucide-react";
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
};

export function PasteNotesForm({ projectId, busy, onBusyChange }: Props) {
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
        <CardHeader className="gap-1.5">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
            >
              <ClipboardPaste className="h-4 w-4" />
            </span>
            <span className="eyebrow">Paste</span>
          </div>
          <CardTitle className="text-base">Paste notes</CardTitle>
          <CardDescription className="leading-relaxed">
            Already have text in a doc? Paste it in to skip uploading a file.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="soft"
            size="sm"
            onClick={() => setOpen(true)}
            disabled={busy}
          >
            <ClipboardPaste className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="ml-1.5">Open paste notes</span>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="gap-1.5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
          >
            <ClipboardPaste className="h-4 w-4" />
          </span>
          <span className="eyebrow">Paste</span>
        </div>
        <CardTitle className="text-base">Paste notes</CardTitle>
        <CardDescription className="leading-relaxed">
          Give it a name and paste the content.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="paste-filename">
              Filename <span className="text-danger" aria-hidden="true">*</span>
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
              className="font-mono"
            />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <Label htmlFor="paste-content">
                Content <span className="text-danger" aria-hidden="true">*</span>
              </Label>
              <span className="text-2xs text-muted-foreground tabular">
                {content.length}/200,000
              </span>
            </div>
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
          </div>
          <div className="flex items-center justify-end gap-2 border-t border-border/70 pt-3">
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
