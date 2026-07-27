"use client";

import Link from "next/link";
import { useProjects } from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { ProjectCard } from "./ProjectCard";
import { ProjectGridSkeleton } from "./ProjectGridSkeleton";

const ErrorHint = ({ message }: { message: string }) => (
  <div className="space-y-1">
    <p>{message}</p>
    <p className="text-xs">
      Make sure the API is running (<code>NEXT_PUBLIC_API_BASE_URL</code>) and Postgres + Redis are
      up (<code>npm run infra:up</code>).
    </p>
  </div>
);

export function ProjectList() {
  const { projects, loading, error } = useProjects();

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="scroll-mt-header text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Upload your project documents and ask grounded questions over them.
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/new">New project</Link>
        </Button>
      </header>

      {error && (
        <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          <ErrorHint message={error} />
        </div>
      )}

      {loading && <ProjectGridSkeleton count={6} />}

      {!loading && projects && projects.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="Create your first project to start uploading briefs and chatting over them."
          actions={
            <Button asChild>
              <Link href="/projects/new">Create a project</Link>
            </Button>
          }
        />
      )}

      {!loading && projects && projects.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}
