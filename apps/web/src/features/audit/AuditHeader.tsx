"use client";

import { Loader2, ShieldCheck, Play } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type Props = {
  running: boolean;
  hasResults: boolean;
  onRun: () => void;
};

export function AuditHeader({ running, hasResults, onRun }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Coverage Audit
          </CardTitle>
          <CardDescription>
            Audit which requirements are covered by tasks and surface risks before delivery.
          </CardDescription>
        </div>
        <Button
          size="sm"
          onClick={onRun}
          disabled={running}
          aria-label={running ? "Audit running…" : "Run coverage audit"}
        >
          {running ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              <span className="ml-1.5">Auditing…</span>
            </>
          ) : (
            <>
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="ml-1.5">{hasResults ? "Re-run audit" : "Run audit"}</span>
            </>
          )}
        </Button>
      </CardHeader>
      {running && (
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            Analyzing requirement coverage and generating findings…
          </div>
        </CardContent>
      )}
    </Card>
  );
}
