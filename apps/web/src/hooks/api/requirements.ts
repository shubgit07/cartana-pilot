"use client";

import * as React from "react";
import { requirementsApi } from "@/lib/api";
import type { RequirementSummary } from "@cartana/shared";
import { messageOf } from "./projects";

export function useRequirements(projectId: string) {
  const [requirements, setRequirements] = React.useState<RequirementSummary[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRequirements(await requirementsApi.list(projectId));
    } catch (e: unknown) {
      setError(messageOf(e) ?? "Failed to load requirements");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  const update = React.useCallback(
    async (
      id: string,
      input: { title?: string; description?: string | null; state?: string }
    ) => {
      const updated = await requirementsApi.update(projectId, id, input);
      await reload();
      return updated;
    },
    [projectId, reload]
  );

  const remove = React.useCallback(
    async (id: string) => {
      await requirementsApi.remove(projectId, id);
      await reload();
    },
    [projectId, reload]
  );

  return { requirements, loading, error, reload, update, remove };
}
