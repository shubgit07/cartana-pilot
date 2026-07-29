"use client";

import Link from "next/link";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { OverviewTab, OverviewTabSkeleton } from "./OverviewTab";
import { ProjectHeader } from "./ProjectHeader";
import { ProjectTabs, type ProjectTabProps } from "./ProjectTabs";
import { useProject } from "@/hooks/api";
import { useQueryState } from "@/hooks/common";
import { NAVIGATION_TABS, type NavigationTab } from "@/lib/constants";
import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";

export function ProjectDetailPage({
  panels,
}: {
  panels: Pick<ProjectTabProps, "sources" | "requirements" | "tasks" | "chat" | "audit">;
}) {
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";
  const router = useRouter();
  const { project, loading, error, reload } = useProject(projectId);
  const [tab, setTab] = useQueryState<NavigationTab>("tab", NAVIGATION_TABS, "overview");

  return (
    <div className="animate-fade-in space-y-6">
      <nav>
        <Link
          href="/"
          className={[
            "group inline-flex items-center gap-1.5 rounded-sm text-sm text-muted-foreground",
            "transition-colors hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          ].join(" ")}
        >
          <ArrowLeft
            className="h-3.5 w-3.5 transition-transform duration-200 ease-out-expo group-hover:-translate-x-0.5"
            aria-hidden="true"
          />
          All projects
        </Link>
      </nav>

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
          <ProjectHeader project={project} onDeleted={() => router.push("/")} />
          <ProjectTabs
            value={tab}
            onValueChange={setTab}
            sourceCount={project.sources.length}
            panels={{
              overview: (
                <OverviewTab
                  sourceCount={project.sources.length}
                  onUploadClick={() => setTab("sources")}
                  onChatClick={() => setTab("chat")}
                  reload={reload}
                />
              ),
              sources: panels.sources,
              requirements: panels.requirements,
              tasks: panels.tasks,
              chat: panels.chat,
              audit: panels.audit,
            }}
          />

          <p className="flex items-center gap-1.5 text-2xs text-muted-foreground">
            <span className="eyebrow">Project ID</span>
            <code className="rounded border border-border/70 bg-surface-sunken px-1.5 py-0.5 font-mono tabular">
              {project.id}
            </code>
          </p>
        </>
      )}

      {loading && <OverviewTabSkeleton />}
    </div>
  );
}

function ProjectHeaderSkeleton() {
  return (
    <Card aria-busy="true" aria-label="Loading project">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-7 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
          <div className="flex gap-2 pt-2">
            <Skeleton className="h-5 w-24 rounded-md" />
            <Skeleton className="h-5 w-36 rounded-md" />
          </div>
        </div>
        <Skeleton className="h-8 w-32 rounded-md" />
      </CardHeader>
    </Card>
  );
}
