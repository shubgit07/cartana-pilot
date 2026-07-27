"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ListTodo } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export function TasksEmpty() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ListTodo className="h-4 w-4" aria-hidden="true" />
          Tasks
        </CardTitle>
        <CardDescription>
          AI-suggested and manually created work items. Accept, edit, create, or relink.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon="inbox"
          title="No tasks yet"
          description="Extracted tasks appear after a document is processed, or create one manually."
        />
      </CardContent>
    </Card>
  );
}
