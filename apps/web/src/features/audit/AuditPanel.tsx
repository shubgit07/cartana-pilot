import { PRTrustBriefDashboard } from "./PRTrustBriefDashboard";

type Props = { projectId: string };

export function AuditPanel({ projectId }: Props) {
  return (
    <section className="mx-auto w-full max-w-5xl pb-10" aria-label="PR Trust Brief">
      <PRTrustBriefDashboard projectId={projectId} />
    </section>
  );
}
