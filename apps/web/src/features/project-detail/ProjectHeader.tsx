"use client";

import { Box, CalendarDays, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useLatestRun } from "@/hooks/api";
import { formatCount, formatDate } from "@/lib/format";
import type { ProjectDetail } from "@cartana/shared";

/**
 * Linear-style project hero: icon tile, title, description, and a strip
 * of real-data pills. No card chrome — hierarchy comes from type scale.
 */
export function ProjectHeader({ project }: { project: ProjectDetail }) {
  return (
    <div className="space-y-3 pt-1">
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="grid size-10 shrink-0 place-items-center rounded-lg bg-warning/10 text-warning"
        >
          <Box className="size-5" />
        </span>
        <div className="min-w-0 space-y-1">
          <h1 className="break-words font-serif text-2xl font-semibold leading-tight tracking-tight">
            {project.name}
          </h1>
          {project.description && (
            <p className="max-w-2xl break-words text-sm leading-relaxed text-muted-foreground">
              {project.description}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 pl-[52px]">
        <Badge variant="muted" className="gap-1">
          <FileText className="h-3 w-3" aria-hidden="true" />
          {formatCount(project.sources.length, "source")}
        </Badge>
        <Badge variant="muted" className="gap-1">
          <CalendarDays className="h-3 w-3" aria-hidden="true" />
          <span>Created</span>
          <time dateTime={project.createdAt} className="tabular" title={project.createdAt}>
            {formatDate(project.createdAt)}
          </time>
        </Badge>
        <AuditStatusPill projectId={project.id} />
      </div>
    </div>
  );
}

/** Live audit status — same honest mapping as the project table rows. */
function AuditStatusPill({ projectId }: { projectId: string }) {
  const { run, loading } = useLatestRun(projectId);

  if (loading) {
    return <Badge variant="muted">…</Badge>;
  }
  if (!run) {
    return <Badge variant="muted">Not audited</Badge>;
  }
  if (run.trustLevel === "low") {
    return (
      <Badge variant="danger" dot>
        Low trust
      </Badge>
    );
  }
  if (run.missingCount > 0) {
    return (
      <Badge variant="warning" dot>
        {run.missingCount} missing
      </Badge>
    );
  }
  return (
    <Badge variant="success" dot>
      Clean
    </Badge>
  );
}
