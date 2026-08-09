"use client";

import * as React from "react";
import { sourcesApi } from "@/lib/api";
import type { SourceStage, SourceSummary } from "@cartana/shared";
import { messageOf } from "./projects";

const POLL_INTERVAL_MS = 1500;
const POLL_BACKOFF_MS = 3000;

export function useSources(projectId: string) {
  const [sources, setSources] = React.useState<SourceSummary[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSources(await sourcesApi.list(projectId));
    } catch (e: unknown) {
      setError(messageOf(e) ?? "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  const uploadFile = React.useCallback(
    async (file: File) => {
      const source = await sourcesApi.uploadFile(projectId, file);
      await reload();
      return source;
    },
    [projectId, reload]
  );

  const createFromText = React.useCallback(
    async (filename: string, content: string) => {
      const source = await sourcesApi.createFromText(projectId, filename, content);
      await reload();
      return source;
    },
    [projectId, reload]
  );

  const createFromDiff = React.useCallback(
    async (filename: string, content: string) => {
      const source = await sourcesApi.createFromDiff(projectId, filename, content);
      await reload();
      return source;
    },
    [projectId, reload]
  );

  const remove = React.useCallback(
    async (sourceId: string) => {
      await sourcesApi.remove(projectId, sourceId);
      await reload();
    },
    [projectId, reload]
  );

  return { sources, loading, error, reload, uploadFile, createFromText, createFromDiff, remove };
}

export interface SourceLiveStatus {
  status: SourceSummary["status"];
  stage: SourceStage;
  chunksTotal: number;
  embedded: number;
  errorMessage: string | null;
}

export function useSourceStatus(projectId: string, sourceId: string | null): SourceLiveStatus | null {
  const [status, setStatus] = React.useState<SourceLiveStatus | null>(null);

  React.useEffect(() => {
    if (!sourceId) {
      setStatus(null);
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      try {
        const s = await sourcesApi.status(projectId, sourceId);
        if (cancelled) return;
        setStatus(s);
        if (s.status === "processing" || s.status === "uploaded") {
          timer = setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch {
        if (!cancelled) timer = setTimeout(tick, POLL_BACKOFF_MS);
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [projectId, sourceId]);

  return status;
}
