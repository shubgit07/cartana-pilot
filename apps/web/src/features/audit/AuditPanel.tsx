"use client";

import * as React from "react";
import { useLatestAudit, useRunAudit } from "@/hooks/api";
import { useToast } from "@/components/ui/toast";
import { AuditHeader } from "./AuditHeader";
import { AuditFindings } from "./AuditFindings";
import { CoverageMatrix } from "./CoverageMatrix";
import { RiskSummary } from "./RiskSummary";
import { AuditEmpty } from "./EmptyState";
import { Skeleton } from "@/components/ui/skeleton";

type Props = { projectId: string };

export function AuditPanel({ projectId }: Props) {
  const { run, loading, reload } = useLatestAudit(projectId);
  const { run: triggerRun, running, error: runError } = useRunAudit(projectId);
  const { toast } = useToast();
  const hasResults = !!run;

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
    // Wait a moment for the job to complete, then reload
    window.setTimeout(() => reload(), 500);
  }

  return (
    <div className="space-y-6">
      <AuditHeader running={running} hasResults={hasResults} onRun={handleRun} />

      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )}

      {!loading && !run && !running && <AuditEmpty />}

      {run && (
        <>
          <RiskSummary run={run} />
          <AuditFindings findings={run.findings} />
          <CoverageMatrix projectId={projectId} />
        </>
      )}
    </div>
  );
}
