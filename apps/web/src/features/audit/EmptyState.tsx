"use client";

import { EmptyState } from "@/components/common/EmptyState";

export function AuditEmpty() {
  return (
    <EmptyState
      icon="inbox"
      title="No audit run yet"
      description="Run an audit to map requirements against tasks, surface coverage gaps, and flag risks before they reach delivery."
    >
      <ul className="grid w-full gap-1.5 text-left text-xs text-muted-foreground">
        <li className="rounded-md border border-border/70 bg-surface-sunken px-3 py-2">
          Coverage scoring for every requirement
        </li>
        <li className="rounded-md border border-border/70 bg-surface-sunken px-3 py-2">
          Critical, warning, and info findings
        </li>
        <li className="rounded-md border border-border/70 bg-surface-sunken px-3 py-2">
          Manual status overrides on any link
        </li>
      </ul>
    </EmptyState>
  );
}
