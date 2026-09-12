"use client";

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Clock,
  GitCommit,
  GitPullRequest,
  History,
  Loader2,
} from "lucide-react";
import { useVerificationRuns } from "@/hooks/api/compliance";
import { formatDateTime } from "@/lib/format";

type Props = {
  projectId: string;
  onSelectRun?: (brief: import("@cartana/shared").PRTrustBrief) => void;
};

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
    <Card>
      <CardHeader className="gap-2 border-b border-border/70 pb-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <span className="eyebrow">Audit Trail</span>
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              Previous Verification Runs ({runs.length})
            </CardTitle>
            <CardDescription>
              Historical PR compliance audits and snapshot verification verdicts.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4">
        {loading && (
          <div className="flex items-center gap-2 py-6 text-xs text-muted-foreground" aria-live="polite">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            Loading…
          </div>
        )}

        {!loading && error && (
          <div className="space-y-2 py-4 text-xs" role="alert">
            <p className="text-foreground">{error}</p>
            <Button size="sm" variant="outline" onClick={() => void reload()}>
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && runs.length === 0 && (
          <div className="py-6 text-center text-xs text-muted-foreground">
            No verification runs yet. Verify a PR to start the audit trail.
          </div>
        )}

        {!loading && !error && runs.length > 0 && (
          <div className="divide-y divide-border/60">
            {runs.map((run) => (
              <div
                key={run.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between py-3 px-2 gap-3 hover:bg-surface-hover/50 rounded-md transition-colors text-xs"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <GitPullRequest className="h-3.5 w-3.5 text-muted-foreground shrink-0" aria-hidden="true" />
                    <span className="font-medium text-foreground truncate">
                      {run.title}
                    </span>
                    <Badge
                      variant={run.trustLevel === "high" ? "success" : run.trustLevel === "medium" ? "warning" : "danger"}
                      className="text-2xs py-0 px-1.5 font-mono uppercase"
                    >
                      {run.trustLevel} Trust
                    </Badge>
                  </div>

                  <div className="flex items-center gap-3 text-2xs text-muted-foreground">
                    {run.commitSha && (
                      <>
                        <span className="flex items-center gap-1 font-mono">
                          <GitCommit className="h-3 w-3" aria-hidden="true" />
                          {run.commitSha}
                        </span>
                        <span>•</span>
                      </>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      {run.createdAt ? formatDateTime(run.createdAt) : "—"}
                    </span>
                    <span>•</span>
                    <span className="font-mono text-foreground">
                      ID: {run.id.slice(0, 12)}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  <div className="text-right">
                    <div className="font-mono text-sm font-bold text-foreground tabular">
                      {run.coverageScore}%
                    </div>
                    <div className="text-2xs text-muted-foreground tabular">
                      {run.coveredCount}/{run.totalRequirements} covered
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleViewReport(run.id)}
                    disabled={loadingRunId === run.id}
                    className="h-8 text-xs font-medium"
                  >
                    {loadingRunId === run.id ? "Loading…" : "View Report"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
