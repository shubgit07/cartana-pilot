"use client";

import * as React from "react";
import Link from "next/link";
import { AlertTriangle, Box, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectHeader } from "./ProjectHeader";
import { ProjectDeleteButton } from "./ProjectDeleteButton";
import { ProjectTabs, type ProjectTabProps } from "./ProjectTabs";
import { useProject } from "@/hooks/api";
import { useQueryState } from "@/hooks/common";
import { NAVIGATION_TABS, type NavigationTab } from "@/lib/constants";
import { useRouter, useParams } from "next/navigation";

export function ProjectDetailPage({
  panels,
}: {
  panels: ProjectTabProps;
}) {
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";
  const router = useRouter();
  const { project, loading, error, reload } = useProject(projectId);
  const [tab, setTab] = useQueryState<NavigationTab>("tab", NAVIGATION_TABS, "requirements");

  return (
    <div className="animate-fade-in space-y-5">
      {/* Linear-style breadcrumb bar: Projects › [icon] name … delete */}
      <div className="flex min-h-[43px] items-center justify-between gap-2 border-b border-border">
        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="flex min-w-0 items-center gap-1 text-[13px]">
            <li className="shrink-0">
              <Link
                href="/"
                className="rounded-md px-1.5 py-1 font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70"
              >
                Projects
              </Link>
            </li>
            <li aria-hidden="true" className="shrink-0 text-muted-foreground">
              <ChevronRight className="h-3.5 w-3.5" />
            </li>
            <li className="flex min-w-0 items-center gap-1.5 font-medium text-foreground">
              <Box className="h-3.5 w-3.5 shrink-0 text-warning" aria-hidden="true" />
              <span aria-current="page" className="truncate">
                {loading ? "…" : (project?.name ?? "Project")}
              </span>
            </li>
          </ol>
        </nav>
        {project && (
          <ProjectDeleteButton
            projectId={project.id}
            projectName={project.name}
            onDeleted={() => router.push("/")}
          />
        )}
      </div>

      {loading && <ProjectHeaderSkeleton />}

      {error && (
        <Card className="border-danger/25 bg-danger-soft">
          <CardHeader className="flex flex-row items-center gap-2 text-sm font-medium text-danger-soft-foreground">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
            Couldn’t load this project
          </CardHeader>
          <CardContent>
            <p role="alert" className="text-sm text-danger-soft-foreground/90">
              {error}
            </p>
          </CardContent>
        </Card>
      )}

      {project && (
        <>
          <ProjectHeader project={project} />
          <ProjectTabs
            value={tab}
            onValueChange={setTab}
            panels={panels}
          />

          <p className="flex items-center gap-1.5 text-2xs text-muted-foreground">
            <span className="eyebrow">Project ID</span>
            <code className="rounded border border-border/70 bg-surface-sunken px-1.5 py-0.5 font-mono tabular">
              {project.id}
            </code>
          </p>
        </>
      )}
    </div>
  );
}

function ProjectHeaderSkeleton() {
  return (
    <div className="space-y-3 pt-1" aria-busy="true" aria-label="Loading project">
      <div className="flex items-start gap-3">
        <Skeleton className="size-10 shrink-0 rounded-lg" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-7 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
      <div className="flex gap-2 pl-[52px]">
        <Skeleton className="h-5 w-24 rounded-full" />
        <Skeleton className="h-5 w-32 rounded-full" />
      </div>
    </div>
  );
}
