"use client";

import * as React from "react";
import { auditApi } from "@/lib/api";
import { messageOf } from "./projects";

export function useVerificationRuns(projectId: string) {
  const [runs, setRuns] = React.useState<
    import("@cartana/shared").VerificationRunSummary[]
  >([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await auditApi.listRuns(projectId);
      setRuns(res.runs);
    } catch (e: unknown) {
      setError(messageOf(e) || "Could not load previous runs.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  const loadBrief = React.useCallback(
    async (runId: string) => auditApi.getRun(projectId, runId),
    [projectId]
  );

  return { runs, loading, error, reload, loadBrief };
}

export function useLatestRun(projectId: string) {
  const { runs, loading } = useVerificationRuns(projectId);
  return { run: runs.length > 0 ? runs[0] : null, loading };
}
