"use client";

import * as React from "react";
import { repositoryApi } from "@/lib/api";
import { messageOf } from "./projects";

export function useRepository(projectId: string) {
  const [status, setStatus] = React.useState<
    import("@cartana/shared").RepositoryStatus | null
  >(null);
  const [pulls, setPulls] = React.useState<
    import("@cartana/shared").GitHubPullItem[]
  >([]);
  const [commits, setCommits] = React.useState<
    import("@cartana/shared").GitHubCommitItem[]
  >([]);
  const [loading, setLoading] = React.useState(true);
  const [syncing, setSyncing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await repositoryApi.getStatus(projectId));
    } catch (e: unknown) {
      setError(messageOf(e) || "Could not load Codebase Index.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  const connectRepo = React.useCallback(
    async (repoUrl: string) => {
      setSyncing(true);
      setError(null);
      try {
        const result = await repositoryApi.connect(projectId, repoUrl);
        await reload();
        return result;
      } catch (e: unknown) {
        const msg = messageOf(e) || "Could not connect that repository.";
        setError(msg);
        throw e;
      } finally {
        setSyncing(false);
      }
    },
    [projectId, reload]
  );

  const resync = React.useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await repositoryApi.resync(projectId);
      await reload();
      return result;
    } catch (e: unknown) {
      const msg = messageOf(e) || "Resync failed.";
      setError(msg);
      throw e;
    } finally {
      setSyncing(false);
    }
  }, [projectId, reload]);

  const disconnectRepo = React.useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      await repositoryApi.disconnect(projectId);
      setPulls([]);
      setCommits([]);
      await reload();
    } catch (e: unknown) {
      const msg = messageOf(e) || "Disconnect failed.";
      setError(msg);
      throw e;
    } finally {
      setSyncing(false);
    }
  }, [projectId, reload]);

  const loadPulls = React.useCallback(async () => {
    const res = await repositoryApi.pulls(projectId);
    setPulls(res.pulls);
    return res.pulls;
  }, [projectId]);

  const loadCommits = React.useCallback(async () => {
    const res = await repositoryApi.commits(projectId);
    setCommits(res.commits);
    return res.commits;
  }, [projectId]);

  return {
    status,
    pulls,
    commits,
    loading,
    syncing,
    error,
    reload,
    connectRepo,
    resync,
    disconnectRepo,
    loadPulls,
    loadCommits,
  };
}
