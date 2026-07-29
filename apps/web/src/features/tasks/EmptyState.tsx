"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ClipboardList } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export function TasksEmpty() {
  return (
    <Card>
      <CardHeader className="gap-1 border-b border-border/70">
        <span className="eyebrow">Workstream</span>
        <CardTitle className="flex items-center gap-2 text-lg">
          <span
            aria-hidden="true"
            className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
          >
            <ClipboardList className="h-4 w-4" />
          </span>
          Tasks
        </CardTitle>
        <CardDescription>
          AI-suggested and manually created work items. Accept, edit, create, or relink.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-5">
        <EmptyState
          icon="inbox"
          title="No tasks yet"
          description="Extracted tasks appear after a document is processed, or create one manually."
        />
      </CardContent>
    </Card>
  );
}
