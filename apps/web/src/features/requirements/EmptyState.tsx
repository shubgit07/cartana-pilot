"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ListChecks } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";

export function RequirementsEmpty() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ListChecks className="h-4 w-4" aria-hidden="true" />
          Requirements
        </CardTitle>
        <CardDescription>
          Extracted from your project material. Accept, edit, or reject each suggestion.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon="inbox"
          title="No requirements yet"
          description="Once you upload a document, extraction will start automatically."
        />
      </CardContent>
    </Card>
  );
}
