"use client";

import { Loader2, Play, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  running: boolean;
  hasResults: boolean;
  onRun: () => void;
  onStop?: () => void;
};

export function AuditHeader({ running, hasResults, onRun, onStop }: Props) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex min-w-0 items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary-soft text-primary shadow-soft"
        >
          <ShieldCheck className="h-5 w-5" />
        </span>

        <div className="min-w-0 space-y-1">
          <h2 className="text-xl font-semibold leading-tight tracking-tight">Audit</h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Check requirement coverage and surface gaps across tasks.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {running && onStop && (
          <Button onClick={onStop} variant="outline" size="sm">
            Stop Audit
          </Button>
        )}
        <Button onClick={onRun} disabled={running}>
          {running ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Running…
            </>
          ) : (
            <>
              <Play className="h-4 w-4" aria-hidden="true" />
              {hasResults ? "Re-run audit" : "Run audit"}
            </>
          )}
        </Button>
      </div>
    </header>
  );
}

