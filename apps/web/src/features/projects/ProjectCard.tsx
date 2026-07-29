"use client";

import Link from "next/link";
import { ArrowUpRight, FileText } from "lucide-react";
import type { ProjectSummary } from "@cartana/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCount, formatDate } from "@/lib/format";

export function ProjectCard({ project }: { project: ProjectSummary }) {
  return (
    <Card
      interactive
      className={[
        "group relative flex h-full flex-col overflow-hidden",
        "transition-[border-color,box-shadow,transform] duration-200 ease-out-expo",
        "hover:-translate-y-0.5 hover:border-border-strong hover:shadow-raised",
        "focus-within:border-border-strong focus-within:shadow-raised",
      ].join(" ")}
    >
      <CardHeader className="gap-1.5">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="min-w-0 text-base leading-snug">
            {/* The stretched pseudo-element makes the whole card a single link target. */}
            <Link
              href={`/projects/${project.id}`}
              className={[
                "rounded-sm after:absolute after:inset-0 after:content-['']",
                "transition-colors group-hover:text-primary",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              ].join(" ")}
            >
              {project.name}
            </Link>
          </CardTitle>
          <ArrowUpRight
            aria-hidden="true"
            className={[
              "mt-0.5 h-4 w-4 shrink-0 text-muted-foreground",
              "opacity-0 transition-all duration-200 ease-out-expo",
              "group-hover:translate-x-0.5 group-hover:opacity-100 group-focus-within:opacity-100",
            ].join(" ")}
          />
        </div>

        {project.description && (
          <CardDescription className="line-clamp-3 break-words leading-relaxed">
            {project.description}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="mt-auto flex items-center justify-between gap-3 border-t border-border/70 pt-4">
        <Badge variant="muted" className="gap-1">
          <FileText className="h-3 w-3" aria-hidden="true" />
          {formatCount(project.sourceCount, "source")}
        </Badge>
        <time
          dateTime={project.createdAt}
          className="text-2xs text-muted-foreground tabular"
          title={project.createdAt}
        >
          {formatDate(project.createdAt)}
        </time>
      </CardContent>
    </Card>
  );
}
