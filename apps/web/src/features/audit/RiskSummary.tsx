"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { AuditRunDetail } from "@cartana/shared";

type Props = { run: AuditRunDetail };

export function RiskSummary({ run }: Props) {
  return (
    <Card className="border-foreground/15">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />
          Risk Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm break-words">{run.summary}</p>

        <div className="grid grid-cols-3 gap-3">
          <StatCard
            icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />}
            label="Covered"
            value={run.coverageLinks.filter((l) => l.status === "covered").length}
          />
          <StatCard
            icon={<AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />}
            label="Partial"
            value={run.coverageLinks.filter((l) => l.status === "partial").length}
          />
          <StatCard
            icon={<XCircle className="h-4 w-4 text-destructive" aria-hidden="true" />}
            label="Missing"
            value={run.coverageLinks.filter((l) => l.status === "missing").length}
          />
        </div>

        <div className="flex gap-4 text-xs text-muted-foreground">
          <span className="tabular">{run.criticalCount} critical</span>
          <span className="tabular">{run.warningCount} warnings</span>
          <span className="tabular">{run.infoCount} info</span>
        </div>
      </CardContent>
    </Card>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-md border bg-muted/30 p-3">
      {icon}
      <span className="text-lg font-semibold tabular">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}
