"use client";

import * as React from "react";
import { AlertTriangle, Info, ListChecks, ShieldAlert, Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import type { AuditFindingSummary } from "@cartana/shared";

type Props = { findings: AuditFindingSummary[] };

type Severity = "critical" | "warning" | "info";

const SEVERITY: Record<
  Severity,
  {
    label: string;
    badge: "danger" | "warning" | "info";
    rail: string;
    tile: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  critical: {
    label: "Critical",
    badge: "danger",
    rail: "bg-danger",
    tile: "border-danger/20 bg-danger-soft/60 text-danger-soft-foreground",
    icon: ShieldAlert,
  },
  warning: {
    label: "Warning",
    badge: "warning",
    rail: "bg-warning",
    tile: "border-warning/20 bg-warning-soft/60 text-warning-soft-foreground",
    icon: AlertTriangle,
  },
  info: {
    label: "Info",
    badge: "info",
    rail: "bg-info",
    tile: "border-info/20 bg-info-soft/60 text-info-soft-foreground",
    icon: Info,
  },
};

const ORDER: Severity[] = ["critical", "warning", "info"];

export function AuditFindings({ findings }: Props) {
  const grouped = React.useMemo(
    () =>
      ORDER.map((severity) => ({
        severity,
        items: findings.filter((f) => f.severity === severity),
      })).filter((g) => g.items.length > 0),
    [findings]
  );

  return (
    <Card>
      <CardHeader className="gap-1 border-b border-border/70">
        <span className="eyebrow">Detected issues</span>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-lg">Findings</CardTitle>
          <span className="text-xs text-muted-foreground tabular">
            {findings.length} total
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-5">
        {grouped.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No findings were raised in this run.
          </p>
        ) : (
          grouped.map((group) => (
            <FindingGroup key={group.severity} severity={group.severity} items={group.items} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function FindingGroup({ severity, items }: { severity: Severity; items: AuditFindingSummary[] }) {
  const config = SEVERITY[severity];
  const Icon = config.icon;

  return (
    <section className="space-y-2.5" aria-labelledby={`findings-${severity}`}>
      <div className="flex items-center gap-2.5">
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-md border",
            config.tile
          )}
        >
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        <h3 id={`findings-${severity}`} className="text-sm font-semibold">
          {config.label}
        </h3>
        <Badge variant={config.badge} dot>
          <span className="tabular">{items.length}</span>
        </Badge>
      </div>

      <ul className="space-y-2">
        {items.map((f) => (
          <li
            key={f.id}
            className={cn(
              "group relative overflow-hidden rounded-lg border border-border/70 bg-surface-sunken",
              "pl-4 pr-3.5 py-3",
              "transition-[border-color,box-shadow] duration-200 ease-out-expo",
              "hover:border-border-strong hover:shadow-card"
            )}
          >
            {/* Severity accent rail */}
            <span
              aria-hidden="true"
              className={cn("absolute inset-y-0 left-0 w-1", config.rail)}
            />

            <p className="break-words text-sm leading-relaxed text-foreground">{f.message}</p>

            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-2xs text-muted-foreground">
              <Badge variant="muted" className="capitalize">
                {f.kind.replace(/_/g, " ")}
              </Badge>

              {f.requirementTitle && (
                <span className="inline-flex min-w-0 items-center gap-1">
                  <Target className="h-3 w-3 shrink-0" aria-hidden="true" />
                  <span className="truncate">{f.requirementTitle}</span>
                </span>
              )}

              {f.taskTitle && (
                <span className="inline-flex min-w-0 items-center gap-1">
                  <ListChecks className="h-3 w-3 shrink-0" aria-hidden="true" />
                  <span className="truncate">{f.taskTitle}</span>
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
