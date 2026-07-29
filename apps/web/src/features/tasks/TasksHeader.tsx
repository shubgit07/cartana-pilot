"use client";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ClipboardList, Plus, RefreshCw } from "lucide-react";

type Props = {
  creating: boolean;
  busy: boolean;
  onToggleCreate: () => void;
  onRefresh: () => void;
};

export function TasksHeader({ creating, busy, onToggleCreate, onRefresh }: Props) {
  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <span className="eyebrow">Delivery</span>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ClipboardList className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              Tasks
            </CardTitle>
            <CardDescription>
              AI-suggested and manually created work items. Accept, edit, create, or relink.
            </CardDescription>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Button size="sm" variant="outline" onClick={onRefresh}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="ml-1.5">Refresh</span>
            </Button>
            <Button
              size="sm"
              variant={creating ? "outline" : "default"}
              onClick={onToggleCreate}
              disabled={busy}
              aria-expanded={creating}
              aria-controls="new-task-card"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="ml-1.5">{creating ? "Hide new task" : "New task"}</span>
            </Button>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}
