"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ListChecks } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export function RequirementsEmpty() {
  return (
    <Card>
      <CardHeader className="gap-1 border-b border-border/70">
        <span className="eyebrow">Scope</span>
        <CardTitle className="flex items-center gap-2 text-lg">
          <ListChecks className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          Requirements
        </CardTitle>
        <CardDescription>
          Extracted from your project material. Accept, edit, or reject each suggestion.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-5">
        <EmptyState
          icon="inbox"
          title="No requirements yet"
          description="Once you upload a document, extraction will start automatically."
        />
      </CardContent>
    </Card>
  );
}
