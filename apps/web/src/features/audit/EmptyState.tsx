"use client";

import { EmptyState } from "@/components/ui/empty-state";

export function AuditEmpty() {
  return (
    <EmptyState
      icon="inbox"
      title="No audit run yet"
      description="Run an audit to map requirements against tasks, surface coverage gaps, and flag risks before they reach delivery."
    >
      <ul className="mx-auto mt-1 grid max-w-md gap-2 text-left text-xs text-muted-foreground sm:grid-cols-3">
        <li className="rounded-md border border-border/70 bg-surface-sunken px-3 py-2">
          Coverage scoring per requirement
        </li>
        <li className="rounded-md border border-border/70 bg-surface-sunken px-3 py-2">
          Critical, warning, and info findings
        </li>
        <li className="rounded-md border border-border/70 bg-surface-sunken px-3 py-2">
          Manual overrides on any link
        </li>
      </ul>
    </EmptyState>
  );
}
