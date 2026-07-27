"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AuditFindingSummary } from "@cartana/shared";

type Props = { findings: AuditFindingSummary[] };

export function AuditFindings({ findings }: Props) {
  if (findings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Findings</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No findings — everything looks good.</p>
        </CardContent>
      </Card>
    );
  }

  const critical = findings.filter((f) => f.severity === "critical");
  const warning = findings.filter((f) => f.severity === "warning");
  const info = findings.filter((f) => f.severity === "info");

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Findings
          <span className="ml-2 text-sm font-normal text-muted-foreground tabular">
            ({findings.length})
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {critical.length > 0 && (
          <FindingGroup
            label="Critical"
            icon={<AlertCircle className="h-4 w-4 text-destructive" aria-hidden="true" />}
            variant="danger"
            findings={critical}
          />
        )}
        {warning.length > 0 && (
          <FindingGroup
            label="Warnings"
            icon={<AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />}
            variant="warning"
            findings={warning}
          />
        )}
        {info.length > 0 && (
          <FindingGroup
            label="Info"
            icon={<Info className="h-4 w-4 text-sky-500" aria-hidden="true" />}
            variant="info"
            findings={info}
          />
        )}
      </CardContent>
    </Card>
  );
}

function FindingGroup({
  label,
  icon,
  variant,
  findings,
}: {
  label: string;
  icon: React.ReactNode;
  variant: "danger" | "warning" | "info";
  findings: AuditFindingSummary[];
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        <span>{label}</span>
        <Badge variant={variant}>
          <span className="tabular">{findings.length}</span>
        </Badge>
      </div>
      <ul className="space-y-1.5">
        {findings.map((f) => (
          <li key={f.id} className="rounded-md border bg-muted/30 p-2.5 text-sm">
            <div className="flex items-start justify-between gap-2">
              <p className="break-words">{f.message}</p>
              <Badge variant="muted" className="shrink-0">
                {f.kind.replace(/_/g, " ")}
              </Badge>
            </div>
            {f.requirementTitle && (
              <p className="mt-1 text-xs text-muted-foreground">
                Requirement: {f.requirementTitle}
              </p>
            )}
            {f.taskTitle && (
              <p className="mt-1 text-xs text-muted-foreground">Task: {f.taskTitle}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
