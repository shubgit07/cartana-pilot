import { EmptyState } from "@/components/common/EmptyState";

export function AuditEmpty() {
  return (
    <EmptyState
      icon="inbox"
      title="No audit run yet"
      description="Run a coverage audit to see which requirements are covered by tasks and what risks exist."
    />
  );
}
