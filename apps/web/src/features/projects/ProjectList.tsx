"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useProjects } from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { ProjectCard } from "./ProjectCard";
import { ProjectGridSkeleton } from "./ProjectGridSkeleton";

const ErrorHint = ({ message }: { message: string }) => (
  <div className="space-y-1">
    <p className="font-medium">{message}</p>
    <p className="text-xs opacity-90">
      Make sure the API is running (<code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code>) and
      Postgres + Redis are up (<code className="font-mono">npm run infra:up</code>).
    </p>
  </div>
);

export function ProjectList() {
  const { projects, loading, error } = useProjects();

  const count = projects?.length ?? 0;

  return (
    <div className="animate-fade-in space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <span className="eyebrow">Workspace</span>
          <h1 className="scroll-mt-header font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            Projects
          </h1>
          <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">
            Upload your project documents and ask grounded questions over them.
            {!loading && count > 0 && (
              <>
                {" "}
                <span className="text-foreground tabular">{count}</span> active.
              </>
            )}
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/new">
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span className="ml-1.5">New project</span>
          </Link>
        </Button>
      </header>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-danger/25 bg-danger-soft p-3 text-sm text-danger-soft-foreground"
        >
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
