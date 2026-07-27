"use client";

import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCount, formatDate } from "@/lib/format";
import { ProjectDeleteButton } from "./ProjectDeleteButton";
import type { ProjectDetail } from "@cartana/shared";

export function ProjectHeader({
  project,
  onDeleted,
}: {
  project: ProjectDetail;
  onDeleted: () => void;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <CardTitle className="text-xl">{project.name}</CardTitle>
          {project.description && (
            <CardDescription className="max-w-2xl break-words">
              {project.description}
            </CardDescription>
          )}
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Badge variant="muted">{formatCount(project.sources.length, "source")}</Badge>
            <Badge variant="muted">
              <span className="mr-1">Created</span>
              <time dateTime={project.createdAt} className="tabular" title={project.createdAt}>
                {formatDate(project.createdAt)}
              </time>
            </Badge>
          </div>
        </div>
        <ProjectDeleteButton
          projectId={project.id}
          projectName={project.name}
          onDeleted={onDeleted}
        />
      </CardHeader>
    </Card>
  );
}
