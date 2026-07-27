import { Badge } from "@/components/ui/badge";
import type { TaskSummary } from "@cartana/shared";

export function TaskStateBadge({
  state,
  origin,
}: {
  state: TaskSummary["state"];
  origin: TaskSummary["origin"];
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
