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
