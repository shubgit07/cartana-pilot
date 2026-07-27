"use client";

import Link from "next/link";
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
    <div className="space-y-6">
      <nav>
        <Link
          href="/"
          className="inline-block rounded-sm text-sm text-muted-foreground hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <span aria-hidden="true">← </span>All projects
        </Link>
      </nav>

      {loading && <ProjectHeaderSkeleton />}
      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader className="text-sm text-destructive">Couldn’t load this project</CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{error}</p>
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
          <p className="text-xs text-muted-foreground">
            Project ID:{" "}
            <code className="rounded bg-muted px-1 py-0.5 tabular">{project.id}</code>
          </p>
        </>
      )}
      {loading && <OverviewTabSkeleton />}
    </div>
  );
}

function ProjectHeaderSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
          <div className="flex gap-2 pt-2">
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-32" />
          </div>
        </div>
        <Skeleton className="h-8 w-32" />
      </CardHeader>
    </Card>
  );
}
