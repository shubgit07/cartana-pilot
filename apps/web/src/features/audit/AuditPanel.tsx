import * as React from "react";
import { GitPullRequest, Layers } from "lucide-react";
import { useLatestAudit, useRunAudit } from "@/hooks/api";
import { useToast } from "@/components/ui/toast";
import { AuditHeader } from "./AuditHeader";
import { AuditFindings } from "./AuditFindings";
import { CoverageMatrix } from "./CoverageMatrix";
import { RiskSummary } from "./RiskSummary";
import { AuditEmpty } from "./EmptyState";
import { PRTrustBriefDashboard } from "./PRTrustBriefDashboard";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";

type Props = { projectId: string };

export function AuditPanel({ projectId }: Props) {
  const [activeTab, setActiveTab] = React.useState<"pr_trust" | "coverage">("pr_trust");
  const { run, loading, reload } = useLatestAudit(projectId);
  const { run: triggerRun, stop: stopRun, running, done, error: runError } = useRunAudit(projectId);
  const { toast } = useToast();
  const hasResults = !!run;

  React.useEffect(() => {
    if (done) {
      reload();
    }
  }, [done, reload]);

  React.useEffect(() => {
    if (runError) {
      toast({
        title: "Audit failed",
        description: runError,
        variant: "destructive",
      });
    }
  }, [runError, toast]);

  async function handleRun() {
    await triggerRun();
  }

  return (
    <section className="mx-auto w-full max-w-5xl space-y-6 pb-10" aria-label="Audit">
      {/* Sub-tab Switcher: PR Trust Brief vs Task Coverage */}
      <div className="flex items-center justify-between border-b border-border/80 pb-3">
        <div className="flex items-center gap-2 rounded-lg bg-muted/60 p-1">
          <button
            type="button"
            onClick={() => setActiveTab("pr_trust")}
            className={cn(
              "flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all",
              activeTab === "pr_trust"
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <GitPullRequest className="h-3.5 w-3.5 text-primary" />
            PR Trust Brief
            <span className="rounded-full bg-primary/15 px-1.5 py-0.2 text-[10px] font-bold text-primary">
              AI Engine
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("coverage")}
            className={cn(
              "flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all",
              activeTab === "coverage"
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
            Task Coverage Matrix
          </button>
        </div>
      </div>

      {activeTab === "pr_trust" ? (
        <PRTrustBriefDashboard projectId={projectId} />
      ) : (
        <div className="space-y-6">
          <AuditHeader running={running} hasResults={hasResults} onRun={handleRun} onStop={stopRun} />

          {loading && (
            <div className="space-y-4" aria-busy="true" aria-label="Loading audit results">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-48 w-full" />
            </div>
          )}

          {!loading && !run && !running && <AuditEmpty />}

          {run && (
            <div className="animate-fade-in space-y-6">
              <RiskSummary run={run} />
              <AuditFindings findings={run.findings} />
              <CoverageMatrix projectId={projectId} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
