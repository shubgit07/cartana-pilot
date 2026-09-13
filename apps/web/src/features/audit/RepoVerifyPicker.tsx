"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, GitCommit, GitPullRequest, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { useRepository } from "@/hooks/api/repository";
import { messageOf } from "@/hooks/api";
import { cn } from "@/lib/cn";

type Props = {
  projectId: string;
  verifying: boolean;
  onVerifyUrl: (url: string) => Promise<unknown>;
};

type Selection = { url: string; headSha: string; label: string } | null;

/** Verify against the connected repo: latest commit, an open PR, or a past commit. */
export function RepoVerifyPicker({ projectId, verifying, onVerifyUrl }: Props) {
  const { toast } = useToast();
  const { status, pulls, commits, loading, loadPulls, loadCommits } = useRepository(projectId);
  const [listsLoading, setListsLoading] = React.useState(false);
  const [selection, setSelection] = React.useState<Selection>(null);

  const connected = status?.connected === true;
  const indexSha = status?.commitSha ?? null;

  React.useEffect(() => {
    if (!connected) return;
    setListsLoading(true);
    Promise.all([loadPulls(), loadCommits()])
      .catch((e: unknown) => {
        toast({
          title: "Could not list PRs",
          description: messageOf(e) ?? "Try again",
          variant: "destructive",
        });
      })
      .finally(() => setListsLoading(false));
    // Load once per connection — loadPulls/loadCommits are stable per projectId.
  }, [connected, projectId, loadPulls, loadCommits, toast]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground" aria-live="polite">
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        Checking repository connection…
      </div>
    );
  }

  if (!connected) {
    return (
      <p className="py-2 text-xs leading-relaxed text-muted-foreground">
        No repository connected yet. Link a public GitHub repo in the{" "}
        <span className="font-medium text-foreground">Repository</span> tab to verify its
        latest commit or open pull requests here — or paste a diff instead.
      </p>
    );
  }

  const stale =
    selection !== null &&
    indexSha !== null &&
    selection.headSha !== "" &&
    !indexSha.startsWith(selection.headSha.slice(0, 7)) &&
    selection.headSha !== indexSha;

  async function handleRun() {
    if (!selection) return;
    try {
      await onVerifyUrl(selection.url);
      toast({ title: "Audit complete", description: "PR Trust Brief successfully generated." });
    } catch (err: unknown) {
      toast({
        title: "Verification failed",
        description: messageOf(err) ?? "Failed to analyze.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="space-y-3">
      {listsLoading && (
        <div className="flex items-center gap-2 py-1 text-xs text-muted-foreground" aria-live="polite">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          Loading pull requests…
        </div>
      )}

      {!listsLoading && pulls.length === 0 && commits.length === 0 && (
        <p className="py-2 text-xs text-muted-foreground">
          No open pull requests or commits found in the connected repository.
        </p>
      )}

      {pulls.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">Open pull requests</p>
          <ul className="space-y-1">
            {pulls.map((pr) => {
              const active = selection?.url === pr.url;
              return (
                <li key={pr.number}>
                  <button
                    type="button"
                    onClick={() =>
                      setSelection({ url: pr.url, headSha: pr.headSha, label: `PR #${pr.number}` })
                    }
                    aria-pressed={active}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left text-xs transition-colors",
                      active
                        ? "border-primary/50 bg-primary-soft/40"
                        : "border-border/60 hover:border-border hover:bg-muted/40"
                    )}
                  >
                    {active ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
                    ) : (
                      <GitPullRequest className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-foreground">
                        #{pr.number} {pr.title}
                      </span>
                      <span className="block truncate font-mono text-2xs text-muted-foreground">
                        head {pr.headSha.slice(0, 7)} · {pr.author ?? "unknown"}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {commits.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">Recent commits</p>
          <ul className="space-y-1">
            {commits.map((commit, i) => {
              const active = selection?.url === commit.url;
              return (
                <li key={commit.sha}>
                  <button
                    type="button"
                    onClick={() =>
                      setSelection({
                        url: commit.url,
                        headSha: commit.sha,
                        label: i === 0 ? "Latest commit" : `Commit ${commit.sha.slice(0, 7)}`,
                      })
                    }
                    aria-pressed={active}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left text-xs transition-colors",
                      active
                        ? "border-primary/50 bg-primary-soft/40"
                        : "border-border/60 hover:border-border hover:bg-muted/40"
                    )}
                  >
                    {active ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
                    ) : (
                      <GitCommit className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-foreground">
                        {i === 0 ? "Latest commit — " : ""}{commit.message || commit.sha.slice(0, 7)}
                      </span>
                      <span className="block truncate font-mono text-2xs text-muted-foreground">
                        {commit.sha.slice(0, 7)}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {stale && selection && (
        <p role="status" className="flex items-start gap-1.5 rounded-md border border-warning/30 bg-warning-soft/40 px-3 py-2 text-xs leading-relaxed text-warning-soft-foreground">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          Codebase Index is at {indexSha?.slice(0, 7)} but {selection.label} points at{" "}
          {selection.headSha.slice(0, 7)}. Verdicts use the indexed code — sync to the PR
          head from the Repository tab for exact context.
        </p>
      )}

      <div className="flex justify-end">
        <Button onClick={() => void handleRun()} disabled={verifying || !selection} className="gap-2">
          {verifying ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing Code & Gaps…
            </>
          ) : (
            <>Run Trust Brief Audit</>
          )}
        </Button>
      </div>
    </div>
  );
}
