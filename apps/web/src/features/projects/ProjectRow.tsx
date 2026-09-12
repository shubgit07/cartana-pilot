"use client";

import Link from "next/link";
import { Box } from "lucide-react";
import type { ProjectSummary } from "@cartana/shared";
import { Badge } from "@/components/ui/badge";
import { useLatestRun } from "@/hooks/api";
import { formatCount, formatDate } from "@/lib/format";
import { cn } from "@/lib/cn";

/**
 * One Linear-style project row: checkbox, title (stretched link),
 * source count, created date, and live audit status.
 */
export function ProjectRow({
  project,
  selected,
  onToggle,
}: {
  project: ProjectSummary;
  selected: boolean;
  onToggle: (id: string, next: boolean) => void;
}) {
  return (
    <tr
      className={cn(
        "group border-b border-border/60 transition-colors last:border-0",
        selected ? "bg-primary-soft/30 hover:bg-primary-soft/40" : "hover:bg-surface-hover/60"
      )}
    >
      {/* Positioned above the stretched title link so it stays clickable. */}
      <td className="relative z-10 w-9 pl-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => onToggle(project.id, e.target.checked)}
          aria-label={`Select ${project.name}`}
          className="block size-3.5 cursor-pointer accent-primary"
        />
      </td>
      {/* Relative so the stretched title link covers this cell (tr can't be a containing block). */}
      <td className="relative min-w-0 px-2 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <Box className="h-3.5 w-3.5 shrink-0 text-warning" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-foreground transition-colors group-hover:text-primary">
            <Link
              href={`/projects/${project.id}`}
              className="rounded-sm after:absolute after:inset-0 after:content-[''] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {project.name}
            </Link>
          </span>
        </div>
        {project.description && (
          <p className="truncate pl-[22px] text-xs text-muted-foreground">{project.description}</p>
        )}
      </td>
      <td className="hidden whitespace-nowrap px-2 py-2.5 sm:table-cell">
        <Badge variant="muted">{formatCount(project.sourceCount, "source")}</Badge>
      </td>
      <td className="hidden whitespace-nowrap px-2 py-2.5 md:table-cell">
        <time
          dateTime={project.createdAt}
          title={project.createdAt}
          className="text-xs text-muted-foreground tabular"
        >
          {formatDate(project.createdAt)}
        </time>
      </td>
      <td className="whitespace-nowrap px-2 py-2.5 pr-3 text-right">
        <StatusCell projectId={project.id} />
      </td>
    </tr>
  );
}

/** Live status from the latest audit run — never invented. */
function StatusCell({ projectId }: { projectId: string }) {
  const { run, loading } = useLatestRun(projectId);

  if (loading) {
    return (
      <span className="text-xs text-muted-foreground" aria-label="Loading status">
        …
      </span>
    );
  }
  if (!run) {
    return <span className="text-xs text-muted-foreground">Not audited</span>;
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
