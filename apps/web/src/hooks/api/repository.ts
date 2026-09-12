"use client";

import * as React from "react";
import { repositoryApi } from "@/lib/api";
import { messageOf } from "./projects";

const MAX_SYNC_FILES = 100;
const MAX_SYNC_BYTES = 150_000;

export function useRepository(projectId: string) {
  const [status, setStatus] = React.useState<
    import("@cartana/shared").RepositoryStatus | null
  >(null);
  const [loading, setLoading] = React.useState(true);
  const [syncing, setSyncing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await repositoryApi.getStatus(projectId));
    } catch (e: unknown) {
      setError(messageOf(e) || "Could not load repository index.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  const syncFiles = React.useCallback(
    async (picked: FileList | File[]) => {
      const pickedFiles = Array.from(picked).slice(0, MAX_SYNC_FILES);
      if (pickedFiles.length === 0) return null;
      setSyncing(true);
      setError(null);
      try {
        const files: { path: string; content: string }[] = [];
        for (const file of pickedFiles) {
          if (file.size > MAX_SYNC_BYTES) continue;
          const content = await file.text();
          const path = (
            file as File & { webkitRelativePath?: string }
          ).webkitRelativePath || file.name;
          files.push({ path, content });
        }
        if (files.length === 0) {
          throw new Error("No readable text files selected.");
        }
        const result = await repositoryApi.sync(projectId, { files });
        await reload();
        return result;
      } catch (e: unknown) {
        const msg = messageOf(e) || "Repository sync failed.";
        setError(msg);
        throw e;
      } finally {
        setSyncing(false);
      }
    },
    [projectId, reload]
  );

  return { status, loading, syncing, error, reload, syncFiles };
}
