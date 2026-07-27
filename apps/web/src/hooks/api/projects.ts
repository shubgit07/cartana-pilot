"use client";

import * as React from "react";
import { projectsApi } from "@/lib/api";
import type { ProjectDetail, ProjectSummary } from "@cartana/shared";

export type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

export function useProjects() {
  const [projects, setProjects] = React.useState<ProjectSummary[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProjects(await projectsApi.list());
    } catch (e: unknown) {
      setError(messageOf(e) ?? "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    reload();
  }, [reload]);

  return { projects, loading, error, reload };
}

export function useProject(projectId: string) {
  const [project, setProject] = React.useState<ProjectDetail | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProject(await projectsApi.get(projectId));
    } catch (e: unknown) {
      setError(messageOf(e) ?? "Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    reload();
  }, [reload]);

  return { project, loading, error, reload };
}

export function messageOf(e: unknown): string | null {
  if (!e) return null;
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return null;
}
