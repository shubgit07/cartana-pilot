import { Badge } from "@/components/ui/badge";
import type { SourceSummary } from "@cartana/shared";

export function SourceStatusBadge({ status }: { status: SourceSummary["status"] }) {
  switch (status) {
    case "processed":
      return <Badge variant="success">Ready</Badge>;
    case "processing":
      return <Badge variant="info">Processing</Badge>;
    case "uploaded":
      return <Badge variant="muted">Queued</Badge>;
    case "failed":
      return <Badge variant="danger">Failed</Badge>;
    default:
      return <Badge variant="muted">{status}</Badge>;
  }
}
