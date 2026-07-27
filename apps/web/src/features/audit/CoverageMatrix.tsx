"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { messageOf, useCoverageLinks } from "@/hooks/api";
import type { CoverageLinkSummary } from "@cartana/shared";

const STATUS_NONE = "__none__";

type Props = { projectId: string };

export function CoverageMatrix({ projectId }: Props) {
  const { links, loading, updateLink } = useCoverageLinks(projectId);
  const { toast } = useToast();

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Coverage Matrix</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading coverage links…</p>
        </CardContent>
      </Card>
    );
  }

  if (!links || links.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Coverage Matrix</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No coverage links yet. Run an audit to generate coverage analysis.
          </p>
        </CardContent>
      </Card>
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
    <Card>
      <CardHeader>
        <CardTitle>
          Coverage Matrix
          <span className="ml-2 text-sm font-normal text-muted-foreground tabular">
            ({links.length})
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y">
          {links.map((link) => (
            <li key={link.id} className="py-3 first:pt-0 last:pb-0">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="text-sm font-medium break-words">
                    {link.requirementTitle}
                  </div>
                  <div className="text-xs text-muted-foreground break-words">
                    <span aria-hidden="true">→ </span>
                    {link.taskTitle}
                  </div>
                  {link.rationale && (
                    <div className="text-xs text-muted-foreground break-words">
                      {link.rationale}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={link.status} />
                  <OriginBadge origin={link.origin} />
                  <Select
                    value={link.status}
                    onValueChange={(v) => handleUpdate(link, v)}
                  >
                    <SelectTrigger className="h-8 w-32" aria-label={`Override coverage status for ${link.requirementTitle}`}>
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
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: CoverageLinkSummary["status"] }) {
  switch (status) {
    case "covered":
      return <Badge variant="success">Covered</Badge>;
    case "partial":
      return <Badge variant="warning">Partial</Badge>;
    case "unclear":
      return <Badge variant="info">Unclear</Badge>;
    case "missing":
      return <Badge variant="danger">Missing</Badge>;
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
