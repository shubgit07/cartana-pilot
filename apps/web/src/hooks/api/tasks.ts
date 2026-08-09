"use client";

import * as React from "react";
import { tasksApi } from "@/lib/api";
import type { TaskSummary } from "@cartana/shared";
import { messageOf } from "./projects";

export function useTasks(projectId: string) {
  const [tasks, setTasks] = React.useState<TaskSummary[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTasks(await tasksApi.list(projectId));
    } catch (e: unknown) {
      setError(messageOf(e) ?? "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  const create = React.useCallback(
    async (input: {
      title: string;
      description?: string | null;
      requirementId?: string | null;
    }) => {
      const created = await tasksApi.create(projectId, input);
      await reload();
      return created;
    },
    [projectId, reload]
  );

  const update = React.useCallback(
    async (
      id: string,
      input: {
        title?: string;
        description?: string | null;
        state?: string;
        requirementId?: string | null;
      }
    ) => {
      const updated = await tasksApi.update(projectId, id, input);
      await reload();
      return updated;
    },
    [projectId, reload]
  );

  const remove = React.useCallback(
    async (id: string) => {
      await tasksApi.remove(projectId, id);
      await reload();
    },
    [projectId, reload]
  );

  return { tasks, loading, error, reload, create, update, remove };
}

const GENERATE_POLL_MS = 1500;
const GENERATE_POLL_BACKOFF_MS = 2500;

/** Kick off on-demand task generation and poll the job until it settles. */
export function useGenerateTasks(projectId: string, onDone?: () => void) {
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
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
    try {
      const result = await tasksApi.generate(projectId);

      const poll = async () => {
        try {
          const status = await tasksApi.generateStatus(projectId, result.jobId);
          const st = (status.state || "").toLowerCase();
          if (st === "completed" || st === "success") {
            setRunning(false);
            onDone?.();
            return;
          }
          if (st === "failed" || st === "failure") {
            setRunning(false);
            setError("Task generation failed. Check the API logs.");
            return;
          }
          timerRef.current = window.setTimeout(poll, GENERATE_POLL_MS);
        } catch {
          timerRef.current = window.setTimeout(poll, GENERATE_POLL_BACKOFF_MS);
        }
      };
      timerRef.current = window.setTimeout(poll, 1000);
    } catch (e: unknown) {
      setRunning(false);
      setError(messageOf(e) ?? "Failed to start task generation");
    }
  }, [projectId, onDone]);

  React.useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  return { run, stop, running, error, setError };
}
