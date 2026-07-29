"use client";

import { CalendarDays, FileText } from "lucide-react";
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
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <span className="eyebrow">Project</span>
          <CardTitle className="break-words font-serif text-xl leading-tight sm:text-2xl">
            {project.name}
          </CardTitle>

          {project.description && (
            <CardDescription className="max-w-2xl break-words leading-relaxed">
              {project.description}
            </CardDescription>
          )}

          <div className="flex flex-wrap items-center gap-2 pt-2.5">
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
