import { Badge } from "@/components/ui/badge";
import type { RequirementSummary } from "@cartana/shared";

export function RequirementStateBadge({
  state,
  origin,
}: {
  state: RequirementSummary["state"];
  origin: RequirementSummary["origin"];
}) {
  switch (state) {
    case "accepted":
      return (
        <Badge variant="success">
          Accepted{origin === "user" ? " · manual" : ""}
        </Badge>
      );
    case "rejected":
      return <Badge variant="muted">Rejected</Badge>;
    case "edited":
      return <Badge variant="warning">Edited</Badge>;
    case "suggested":
    default:
      return (
        <Badge variant="info">
          Suggested{origin === "ai" ? " · AI" : ""}
        </Badge>
      );
  }
}
