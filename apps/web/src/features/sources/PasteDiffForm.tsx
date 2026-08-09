"use client";

import * as React from "react";
import { GitPullRequest, Code2, Copy, Check } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SubmitButton } from "@/components/common/SubmitButton";
import { useToast } from "@/components/ui/toast";
import { useSources, messageOf } from "@/hooks/api";

const GIT_CMD = "git diff origin/main...HEAD";

type Props = {
  projectId: string;
  busy: boolean;
  onBusyChange: (next: boolean) => void;
  onUploaded?: () => void;
};

export function PasteDiffForm({ projectId, busy, onBusyChange, onUploaded }: Props) {
  const [open, setOpen] = React.useState(false);
  const [mode, setMode] = React.useState<"paste" | "github">("paste");
  const [filename, setFilename] = React.useState("feature-implementation.diff");
  const [content, setContent] = React.useState("");
  const [githubUrl, setGithubUrl] = React.useState("");
  const [copied, setCopied] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  
  const { createFromDiff } = useSources(projectId);
  const { toast } = useToast();

  function copyGitCommand() {
    navigator.clipboard.writeText(GIT_CMD);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleanFilename = filename.trim() || "implementation.diff";
    const payloadContent = mode === "github" ? `github_pr:${githubUrl.trim()}` : content.trim();

    if (!payloadContent) return;

    setSubmitting(true);
    onBusyChange(true);
    try {
      await createFromDiff(cleanFilename, payloadContent);
      onUploaded?.();
      setContent("");
      setGithubUrl("");
      setOpen(false);

      toast({
        title: "Implementation Diff attached",
        description: `${cleanFilename} attached & noise filtered.`,
      });
    } catch (err: unknown) {
      toast({
        title: "Could not add implementation diff",
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
      <Card className="border-border/70 shadow-sm transition-all hover:border-primary/40">
        <CardHeader className="gap-1.5">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
            >
              <GitPullRequest className="h-4 w-4" />
            </span>
            <span className="eyebrow">Implementation Code</span>
          </div>
          <CardTitle className="text-base">Attach Git Diff or PR</CardTitle>
          <CardDescription className="leading-relaxed">
            Paste terminal diff output or give a public GitHub PR URL to audit against your requirements.
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
            <Code2 className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="ml-1.5">Attach Git Diff / PR URL</span>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/70 shadow-sm">
      <CardHeader className="gap-1.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
            >
              <GitPullRequest className="h-4 w-4" />
            </span>
            <span className="eyebrow">Implementation Code</span>
          </div>

          <div className="flex items-center rounded-lg border border-border/80 bg-surface-sunken p-0.5">
            <button
              type="button"
              onClick={() => setMode("paste")}
              className={`rounded-md px-2.5 py-1 text-2xs font-medium transition-colors ${
                mode === "paste"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Paste Diff
            </button>
            <button
              type="button"
              onClick={() => setMode("github")}
              className={`rounded-md px-2.5 py-1 text-2xs font-medium transition-colors ${
                mode === "github"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              GitHub PR URL
            </button>
          </div>
        </div>

        <CardTitle className="text-base">Attach Implementation Code</CardTitle>
        <CardDescription className="leading-relaxed">
          {mode === "paste"
            ? "Paste raw git diff output from your terminal."
            : "Paste a public GitHub Pull Request URL to fetch changes directly."}
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {mode === "paste" && (
            <>
              {/* Copyable Terminal Command Banner */}
              <div className="flex items-center justify-between gap-2 rounded-lg border border-border/70 bg-surface-sunken px-3 py-2 text-xs">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <span className="font-mono text-2xs text-primary">Terminal Command:</span>
                  <code className="font-mono text-foreground">{GIT_CMD}</code>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={copyGitCommand}
                  className="shrink-0"
                >
                  {copied ? (
                    <>
                      <Check className="h-3 w-3 text-success" />
                      <span className="ml-1 text-2xs">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span className="ml-1 text-2xs">Copy</span>
                    </>
                  )}
                </Button>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="diff-filename">
                  Filename Reference <span className="text-danger" aria-hidden="true">*</span>
                </Label>
                <Input
                  id="diff-filename"
                  autoComplete="off"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  placeholder="e.g. pr-102-implementation.diff"
                  className="font-mono"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <Label htmlFor="diff-content">
                    Git Diff Content <span className="text-danger" aria-hidden="true">*</span>
                  </Label>
                  <span className="text-2xs text-muted-foreground tabular">
                    {content.length}/500,000 chars
                  </span>
                </div>
                <Textarea
                  id="diff-content"
                  rows={8}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  maxLength={500_000}
                  placeholder="Paste terminal diff (git diff origin/main...HEAD)..."
                  className="font-mono text-xs leading-relaxed"
                  required
                />
              </div>
            </>
          )}

          {mode === "github" && (
            <div className="space-y-1.5">
              <Label htmlFor="github-url">
                GitHub Pull Request URL <span className="text-danger" aria-hidden="true">*</span>
              </Label>
              <Input
                id="github-url"
                type="url"
                autoComplete="off"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/facebook/react/pull/28000"
                className="font-mono text-xs"
                required
              />
              <p className="text-2xs text-muted-foreground">
                Public GitHub repository PRs will be fetched automatically via GitHub API.
              </p>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 border-t border-border/70 pt-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setOpen(false);
                setContent("");
                setGithubUrl("");
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
            <SubmitButton
              type="submit"
              loading={submitting}
              loadingLabel="Attaching…"
              disabled={mode === "paste" ? !content.trim() : !githubUrl.trim()}
            >
              Attach Implementation
            </SubmitButton>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
