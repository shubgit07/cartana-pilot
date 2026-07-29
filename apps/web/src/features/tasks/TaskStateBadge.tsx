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
        <Badge variant="success" dot>
          Accepted{origin === "user" ? " \u00b7 manual" : ""}
        </Badge>
      );
    case "rejected":
      return <Badge variant="muted">Rejected</Badge>;
    case "edited":
      return (
        <Badge variant="warning" dot>
          Edited
        </Badge>
      );
    case "suggested":
    default:
      return (
        <Badge variant="info" dot>
          Suggested{origin === "ai" ? " \u00b7 AI" : ""}
        </Badge>
      );
  }
}
