"use client";

import * as React from "react";
import { auditApi } from "@/lib/api";
import type {
  AuditRunDetail,
  AuditRunSummary,
  CoverageLinkSummary,
} from "@cartana/shared";
import { messageOf } from "./projects";

export function useLatestAudit(projectId: string) {
  const [run, setRun] = React.useState<AuditRunDetail | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await auditApi.getLatest(projectId);
      setRun(result ?? null);
    } catch (e: unknown) {
      const msg = messageOf(e);
      // 404 means no audit run yet — not an error state
      if (msg && !msg.includes("No audit run")) {
        setError(msg);
      }
      setRun(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  return { run, loading, error, reload };
}

export function useRunAudit(projectId: string) {
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [done, setDone] = React.useState(false);

  const run = React.useCallback(async () => {
    setRunning(true);
    setError(null);
    setDone(false);
    setJobId(null);
    try {
      const result = await auditApi.runAudit(projectId);
      setJobId(result.jobId);

      // Poll for completion
      const poll = async () => {
        try {
          const status = await auditApi.jobStatus(projectId, result.jobId);
          if (status.state === "completed") {
            setRunning(false);
            setDone(true);
            return;
          }
          if (status.state === "failed") {
            setRunning(false);
            setError("Audit job failed. Check the API logs.");
            return;
          }
          // Still waiting or active — keep polling
          window.setTimeout(poll, 2000);
        } catch {
          window.setTimeout(poll, 3000);
        }
      };
      window.setTimeout(poll, 1500);
    } catch (e: unknown) {
      setRunning(false);
      setError(messageOf(e) ?? "Failed to start audit");
    }
  }, [projectId]);

  return { run, running, error, jobId, done, setDone };
}

export function useCoverageLinks(projectId: string) {
  const [links, setLinks] = React.useState<CoverageLinkSummary[] | null>(null);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    setLoading(true);
    try {
      setLinks(await auditApi.listCoverageLinks(projectId));
    } catch {
      setLinks(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  const updateLink = React.useCallback(
    async (linkId: string, input: { status?: string; rationale?: string | null }) => {
      const updated = await auditApi.updateCoverageLink(projectId, linkId, input);
      await reload();
      return updated;
    },
    [projectId, reload]
  );

  return { links, loading, reload, updateLink };
}

export function useAuditRuns(projectId: string) {
  const [runs, setRuns] = React.useState<AuditRunSummary[]>([]);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    setLoading(true);
    try {
      setRuns(await auditApi.listRuns(projectId));
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  return { runs, loading, reload };
}
