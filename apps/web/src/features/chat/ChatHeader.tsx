"use client";

import { RefreshCw, MessagesSquare } from "lucide-react";
import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function ChatHeader({ canReset, onReset }: { canReset: boolean; onReset: () => void }) {
  return (
    <CardHeader className="flex flex-row items-start justify-between gap-3 border-b border-border/70">
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary-soft-foreground"
        >
          <MessagesSquare className="h-4 w-4" />
        </span>
        <div className="space-y-0.5">
          <CardTitle>Project chat</CardTitle>
          <CardDescription>
            Grounded answers with citations to your uploaded sources.
          </CardDescription>
        </div>
      </div>
      {canReset && (
        <Button size="sm" variant="ghost" onClick={onReset}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Reset</span>
        </Button>
      )}
    </CardHeader>
  );
}
