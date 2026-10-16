"use client";

import * as React from "react";
import { GitCommit, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVerificationRuns } from "@/hooks/api/compliance";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { PRTrustBrief } from "@cartana/shared";

type Props = {
  projectId: string;
  onSelectRun?: (brief: PRTrustBrief) => void;
};

/**
 * Audit trail as an accounting table: one row per run, hairline rules,
 * uppercase column labels, tabular figures, sentence-case copy.
 */
export function PreviousRunsView({ projectId, onSelectRun }: Props) {
  const { runs, loading, error, reload, loadBrief } = useVerificationRuns(projectId);
  const [loadingRunId, setLoadingRunId] = React.useState<string | null>(null);

  const handleViewReport = async (runId: string) => {
    setLoadingRunId(runId);
    try {
      const brief = await loadBrief(runId);
      onSelectRun?.(brief);
    } catch {
      // Error surfaces via the runs hook state on reload; keep the row usable.
    } finally {
      setLoadingRunId(null);
    }
  };

  return (
    <section className="rounded-md border border-border bg-card">
      <header className="flex items-baseline justify-between border-b border-border px-4 py-3">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h2 className="mt-1 text-base font-semibold text-foreground">
            Previous verification runs
          </h2>
        </div>
        <span className="font-mono text-xs text-muted-foreground tabular">{runs.length}</span>
      </header>

      <div>
        {loading && (
          <div
            className="flex items-center gap-2 px-4 py-6 text-xs text-muted-foreground"
            aria-live="polite"
          >
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            Loading
          </div>
        )}

        {!loading && error && (
          <div className="space-y-2 px-4 py-4 text-xs" role="alert">
            <p className="text-foreground">{error}</p>
            <Button size="sm" variant="outline" onClick={() => void reload()}>
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && runs.length === 0 && (
          <p className="px-4 py-6 text-center text-xs text-muted-foreground">
            No verification runs yet. Verify a pull request to start the audit trail.
          </p>
        )}

        {!loading && !error && runs.length > 0 && (
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="eyebrow px-4 py-2 text-left font-semibold">Run</th>
                <th className="eyebrow px-4 py-2 text-left font-semibold">Commit</th>
                <th className="eyebrow px-4 py-2 text-left font-semibold">Generated</th>
                <th className="eyebrow px-4 py-2 text-right font-semibold">Coverage</th>
                <th className="eyebrow px-4 py-2 text-right font-semibold">Trust</th>
                <th className="px-4 py-2" aria-hidden="true" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {runs.map((run) => (
                <tr key={run.id} className="transition-colors hover:bg-muted/20">
                  <td className="max-w-[18rem] px-4 py-3">
                    <span className="block truncate font-medium text-foreground">{run.title}</span>
                    <span className="font-mono text-2xs text-muted-foreground">
                      {run.id.slice(0, 12)}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-2xs text-muted-foreground">
                    {run.commitSha ? (
                      <span className="flex items-center gap-1">
                        <GitCommit className="h-3 w-3" aria-hidden="true" />
                        {run.commitSha}
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="px-4 py-3 text-2xs text-muted-foreground">
                    {run.createdAt ? formatDateTime(run.createdAt) : "-"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right font-mono tabular">
                    <span className="text-foreground">{run.coverageScore}%</span>{" "}
                    <span className="text-2xs text-muted-foreground">
                      {run.coveredCount}/{run.totalRequirements}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span
                      className={cn(
                        "font-mono text-2xs font-semibold uppercase tracking-[0.04em]",
                        run.trustLevel === "high"
                          ? "text-success"
                          : run.trustLevel === "medium"
                            ? "text-warning"
                            : "text-danger"
                      )}
                    >
                      {run.trustLevel}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void handleViewReport(run.id)}
                      disabled={loadingRunId === run.id}
                      className="h-7 text-2xs"
                    >
                      {loadingRunId === run.id ? "Loading" : "View report"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
