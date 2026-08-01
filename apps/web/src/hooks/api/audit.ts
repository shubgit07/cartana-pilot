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
  const timerRef = React.useRef<number | null>(null);

  const stop = React.useCallback(() => {
    setRunning(false);
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const run = React.useCallback(async () => {
    setRunning(true);
    setError(null);
    setDone(false);
    setJobId(null);
    try {
      const result = await auditApi.runAudit(projectId);
      setJobId(result.jobId);

      const poll = async () => {
        try {
          const status = await auditApi.jobStatus(projectId, result.jobId);
          const st = (status.state || "").toLowerCase();
          if (st === "completed" || st === "success") {
            setRunning(false);
            setDone(true);
            return;
          }
          if (st === "failed" || st === "failure") {
            setRunning(false);
            setError("Audit job failed. Check the API logs.");
            return;
          }
          timerRef.current = window.setTimeout(poll, 1500);
        } catch {
          timerRef.current = window.setTimeout(poll, 2500);
        }
      };
      timerRef.current = window.setTimeout(poll, 1000);
    } catch (e: unknown) {
      setRunning(false);
      setError(messageOf(e) ?? "Failed to start audit");
    }
  }, [projectId]);

  React.useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  return { run, stop, running, error, jobId, done, setDone };
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
