"use client";

import * as React from "react";
import { Check, FileText, Loader2, Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RequirementStateBadge } from "./RequirementStateBadge";
import { RequirementEditForm } from "./RequirementEditForm";
import { cn } from "@/lib/cn";
import type { RequirementSummary } from "@cartana/shared";

type Props = {
  requirement: RequirementSummary;
  onAccept: () => void;
  onReject: () => void;
  onSave: (patch: { title?: string; description?: string | null }) => Promise<void>;
  onDelete: () => void;
};

export function RequirementRow({ requirement: r, onAccept, onReject, onSave, onDelete }: Props) {
  const [editing, setEditing] = React.useState(false);
  const [pending, setPending] = React.useState<"accept" | "reject" | null>(null);

  const isDecided = r.state === "accepted" || r.state === "rejected";
  const isHidden = r.state === "rejected";

  async function doAccept() {
    setPending("accept");
    try {
      await onAccept();
    } finally {
      setPending(null);
    }
  }
  async function doReject() {
    setPending("reject");
    try {
      await onReject();
    } finally {
      setPending(null);
    }
  }

  return (
    <div className={cn(isHidden && "opacity-60")}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          {editing ? (
            <RequirementEditForm
              initialTitle={r.title}
              initialDescription={r.description}
              saving={false}
              onCancel={() => setEditing(false)}
              onSave={async (patch) => {
                await onSave(patch);
                setEditing(false);
              }}
            />
          ) : (
            <>
              <h3 className="text-sm font-medium">{r.title}</h3>
              {r.description && (
                <p className="mt-1 text-sm break-words text-muted-foreground">{r.description}</p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <RequirementStateBadge state={r.state} origin={r.origin} />
                {r.sourceLinks.length > 0 && (
                  <span className="inline-flex items-center gap-1">
                    <FileText className="h-3 w-3" aria-hidden="true" />
                    {r.sourceLinks.map((s) => s.filename).join(", ")}
                  </span>
                )}
              </div>
            </>
          )}
        </div>

        {!editing && (
          <div className="flex flex-wrap items-center gap-2 sm:justify-end">
            {!isDecided && (
              <>
                <Button
                  size="sm"
                  onClick={doAccept}
                  disabled={pending !== null}
                  aria-label={`Accept requirement "${r.title}"`}
                >
                  {pending === "accept" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  ) : (
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  <span className="ml-1.5">Accept</span>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={doReject}
                  disabled={pending !== null}
                  aria-label={`Reject requirement "${r.title}"`}
                >
                  {pending === "reject" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  ) : (
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  <span className="ml-1.5">Reject</span>
                </Button>
              </>
            )}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setEditing(true)}
              aria-label={`Edit requirement "${r.title}"`}
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={onDelete}
              aria-label={`Delete requirement "${r.title}"`}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
