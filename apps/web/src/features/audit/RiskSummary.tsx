"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, CircleDashed, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import type { AuditRunDetail } from "@cartana/shared";

type Props = { run: AuditRunDetail };

type Tone = "success" | "warning" | "info" | "danger";

/** Soft surface + accent pairing per tone, resolved through theme tokens. */
const TONE_TILE: Record<Tone, string> = {
  success: "border-success/20 bg-success-soft/60 text-success-soft-foreground",
  warning: "border-warning/20 bg-warning-soft/60 text-warning-soft-foreground",
  info: "border-info/20 bg-info-soft/60 text-info-soft-foreground",
  danger: "border-danger/20 bg-danger-soft/60 text-danger-soft-foreground",
};

const TONE_BAR: Record<Tone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  info: "bg-info",
  danger: "bg-danger",
};

export function RiskSummary({ run }: Props) {
  const links = run.coverageLinks;
  const total = links.length;

  const covered = links.filter((l) => l.status === "covered").length;
  const partial = links.filter((l) => l.status === "partial").length;
  const unclear = links.filter((l) => l.status === "unclear").length;
  const missing = links.filter((l) => l.status === "missing").length;

  const coveragePct = total === 0 ? 0 : Math.round((covered / total) * 100);

  /** Segments of the stacked meter, in severity order. */
  const segments: Array<{ tone: Tone; value: number; label: string }> = [
    { tone: "success", value: covered, label: "Covered" },
    { tone: "warning", value: partial, label: "Partial" },
    { tone: "info", value: unclear, label: "Unclear" },
    { tone: "danger", value: missing, label: "Missing" },
  ];

  return (
    <Card>
      <CardHeader className="gap-4 border-b border-border/70">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <span className="eyebrow">Audit overview</span>
            <CardTitle className="text-lg">Risk summary</CardTitle>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="font-serif text-3xl font-semibold leading-none tracking-tight tabular">
              {coveragePct}%
            </span>
            <span className="text-xs text-muted-foreground">covered</span>
          </div>
        </div>

        {/* Stacked coverage meter — one bar communicates the whole distribution. */}
        <div
          className="flex h-2 w-full overflow-hidden rounded-full bg-surface-sunken"
          role="progressbar"
          aria-valuenow={coveragePct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Requirement coverage: ${coveragePct} percent covered`}
        >
          {total > 0 &&
            segments.map((s) =>
              s.value === 0 ? null : (
                <span
                  key={s.tone}
                  className={cn("h-full transition-[width] duration-500 ease-out-expo", TONE_BAR[s.tone])}
                  style={{ width: `${(s.value / total) * 100}%` }}
                  title={`${s.label}: ${s.value}`}
                />
              )
            )}
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-5">
        {run.summary && (
          <p className="break-words text-sm leading-relaxed text-muted-foreground">{run.summary}</p>
        )}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            tone="success"
            icon={<CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
            label="Covered"
            value={covered}
          />
          <StatTile
            tone="warning"
            icon={<AlertTriangle className="h-4 w-4" aria-hidden="true" />}
            label="Partial"
            value={partial}
          />
          <StatTile
            tone="info"
            icon={<CircleDashed className="h-4 w-4" aria-hidden="true" />}
            label="Unclear"
            value={unclear}
          />
          <StatTile
            tone="danger"
            icon={<XCircle className="h-4 w-4" aria-hidden="true" />}
            label="Missing"
            value={missing}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-border/70 pt-4">
          <span className="eyebrow mr-1">Findings</span>
          <Badge variant="danger" dot>
            <span className="tabular">{run.criticalCount}</span> critical
          </Badge>
          <Badge variant="warning" dot>
            <span className="tabular">{run.warningCount}</span> warnings
          </Badge>
          <Badge variant="info" dot>
            <span className="tabular">{run.infoCount}</span> info
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function StatTile({
  tone,
  icon,
  label,
  value,
}: {
  tone: Tone;
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1.5 rounded-lg border p-3.5",
        "transition-[background-color,border-color,box-shadow] duration-200 ease-out-expo",
        "hover:shadow-card",
        TONE_TILE[tone]
      )}
    >
      <span className="flex items-center gap-1.5 text-xs font-medium">
        {icon}
        {label}
      </span>
      <span className="text-2xl font-semibold leading-none tabular">{value}</span>
    </div>
  );
}
