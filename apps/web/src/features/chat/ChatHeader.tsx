"use client";

import { RefreshCw, BookOpen } from "lucide-react";
import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function ChatHeader({ canReset, onReset }: { canReset: boolean; onReset: () => void }) {
  return (
    <CardHeader className="flex flex-row items-start justify-between gap-3">
      <div className="space-y-1">
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-4 w-4" aria-hidden="true" />
          Project chat
        </CardTitle>
        <CardDescription>Grounded answers with citations to your uploaded sources.</CardDescription>
      </div>
      {canReset && (
        <Button size="sm" variant="outline" onClick={onReset}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          <span className="ml-1.5">Reset</span>
        </Button>
      )}
    </CardHeader>
  );
}
