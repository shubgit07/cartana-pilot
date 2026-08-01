import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { SourceSummary } from "@cartana/shared";

/**
 * Status pill for a source. Colour comes from the semantic badge
 * variants; "Processing" swaps the static dot for a spinner so the
 * state reads as live. The spinner is motion-safe: it never animates
 * for users who prefer reduced motion.
 */
export function SourceStatusBadge({ status }: { status: SourceSummary["status"] }) {
  switch (status) {
    case "processed":
      return (
        <Badge variant="success" dot>
          Ready
        </Badge>
      );
    case "processing":
      return (
        <Badge variant="info">
          <Loader2 className="size-3 motion-safe:animate-spin" aria-hidden="true" />
          Processing
        </Badge>
      );
    case "uploaded":
      return (
        <Badge variant="muted" dot>
          Queued
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="danger" dot>
          Failed
        </Badge>
      );
    default:
      return <Badge variant="muted">{status}</Badge>;
  }
}
