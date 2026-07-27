"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

type Props = {
  creating: boolean;
  busy: boolean;
  onToggleCreate: () => void;
  onRefresh: () => void;
};

export function TasksHeader({ creating, busy, onToggleCreate, onRefresh }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Tasks
          </CardTitle>
          <CardDescription>
            AI-suggested and manually created work items. Accept, edit, create, or relink.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={onRefresh}>
            Refresh
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
      </CardHeader>
      <CardContent className="hidden" />
    </Card>
  );
}
