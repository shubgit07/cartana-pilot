"use client";

import Link from "next/link";
import type { ProjectSummary } from "@cartana/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCount, formatDate } from "@/lib/format";

export function ProjectCard({ project }: { project: ProjectSummary }) {
  return (
    <Card className="transition-colors hover:border-foreground/20 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
      <CardHeader>
        <CardTitle>
          <Link
            href={`/projects/${project.id}`}
            className="rounded-sm transition-colors hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {project.name}
          </Link>
        </CardTitle>
        {project.description && (
          <CardDescription className="line-clamp-3 break-words">
            {project.description}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <Badge variant="muted">
          {formatCount(project.sourceCount, "source")}
        </Badge>
        <time
          dateTime={project.createdAt}
          className="text-xs text-muted-foreground tabular"
          title={project.createdAt}
        >
          {formatDate(project.createdAt)}
        </time>
      </CardContent>
    </Card>
  );
}
