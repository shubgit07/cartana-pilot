"use client";

import { ArrowRight, Grid2x2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { messageOf, useCoverageLinks } from "@/hooks/api";
import { cn } from "@/lib/cn";
import type { CoverageLinkSummary } from "@cartana/shared";

const STATUS_NONE = "__none__";

type Props = { projectId: string };

const STATUS_RAIL: Record<string, string> = {
  covered: "bg-success",
  partial: "bg-warning",
  unclear: "bg-info",
  missing: "bg-danger",
};

function MatrixShell({ count, children }: { count?: number; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="gap-1 border-b border-border/70">
        <span className="eyebrow">Traceability</span>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Grid2x2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Coverage matrix
          </CardTitle>
          {typeof count === "number" && (
            <span className="text-xs text-muted-foreground tabular">{count} links</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-5">{children}</CardContent>
    </Card>
  );
}

export function CoverageMatrix({ projectId }: Props) {
  const { links, loading, updateLink } = useCoverageLinks(projectId);
  const { toast } = useToast();

  if (loading) {
    return (
      <MatrixShell>
        <div className="space-y-2" aria-busy="true" aria-label="Loading coverage links">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </MatrixShell>
    );
  }

  if (!links || links.length === 0) {
    return (
      <MatrixShell count={0}>
        <p className="py-6 text-center text-sm text-muted-foreground">
          No coverage links yet. Run an audit to generate coverage analysis.
        </p>
      </MatrixShell>
    );
  }

  async function handleUpdate(link: CoverageLinkSummary, status: string) {
    try {
      await updateLink(link.id, { status: status === STATUS_NONE ? undefined : status });
      toast({ title: "Coverage updated" });
    } catch (e: unknown) {
      toast({
        title: "Update failed",
        description: messageOf(e) ?? "Try again",
        variant: "destructive",
      });
    }
  }

  return (
    <MatrixShell count={links.length}>
      <ul className="space-y-2">
        {links.map((link) => (
          <li
            key={link.id}
            className={cn(
              "group relative overflow-hidden rounded-lg border border-border/70 bg-surface-sunken",
              "py-3 pl-4 pr-3.5",
              "transition-[border-color,box-shadow] duration-200 ease-out-expo",
              "hover:border-border-strong hover:shadow-card"
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "absolute inset-y-0 left-0 w-1",
                STATUS_RAIL[link.status] ?? "bg-border-strong"
              )}
            />

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1 space-y-1">
                <div className="break-words text-sm font-medium">{link.requirementTitle}</div>

                <div className="flex min-w-0 items-start gap-1.5 text-xs text-muted-foreground">
                  <ArrowRight className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
                  <span className="break-words">{link.taskTitle}</span>
                </div>

                {link.rationale && (
                  <p className="break-words text-xs leading-relaxed text-muted-foreground/80">
                    {link.rationale}
                  </p>
                )}
              </div>

              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <StatusBadge status={link.status} />
                <OriginBadge origin={link.origin} />
                <Select value={link.status} onValueChange={(v) => handleUpdate(link, v)}>
                  <SelectTrigger
                    className="h-8 w-32"
                    aria-label={`Override coverage status for ${link.requirementTitle}`}
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="covered">Covered</SelectItem>
                    <SelectItem value="partial">Partial</SelectItem>
                    <SelectItem value="unclear">Unclear</SelectItem>
                    <SelectItem value="missing">Missing</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </MatrixShell>
  );
}

function StatusBadge({ status }: { status: CoverageLinkSummary["status"] }) {
  switch (status) {
    case "covered":
      return <Badge variant="success" dot>Covered</Badge>;
    case "partial":
      return <Badge variant="warning" dot>Partial</Badge>;
    case "unclear":
      return <Badge variant="info" dot>Unclear</Badge>;
    case "missing":
      return <Badge variant="danger" dot>Missing</Badge>;
    default:
      return <Badge variant="muted">{status}</Badge>;
  }
}

function OriginBadge({ origin }: { origin: CoverageLinkSummary["origin"] }) {
  if (origin === "user-confirmed") {
    return <Badge variant="muted">Manual</Badge>;
  }
  return null;
}
