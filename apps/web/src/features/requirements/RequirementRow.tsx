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

/** Left rail colour per requirement state, resolved through theme tokens. */
const STATE_RAIL: Record<string, string> = {
  accepted: "bg-success",
  edited: "bg-warning",
  suggested: "bg-info",
  rejected: "bg-border-strong",
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
    <div
      className={cn(
        "group relative overflow-hidden rounded-lg border border-border/70 bg-surface",
        "py-3.5 pl-4 pr-3.5",
        "transition-[border-color,box-shadow,opacity] duration-200 ease-out-expo",
        "hover:border-border-strong hover:shadow-card",
        isHidden && "opacity-60"
      )}
    >
      <span
        aria-hidden="true"
        className={cn("absolute inset-y-0 left-0 w-1", STATE_RAIL[r.state] ?? "bg-border-strong")}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
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
              <h3
                className={cn(
                  "break-words text-sm font-medium leading-snug",
                  isHidden && "line-through decoration-border-strong"
                )}
              >
                {r.title}
              </h3>

              {r.description && (
                <p className="mt-1 break-words text-sm leading-relaxed text-muted-foreground">
                  {r.description}
                </p>
              )}

              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <RequirementStateBadge state={r.state} origin={r.origin} />

                {r.sourceLinks.map((s) => (
                  <span
                    key={s.filename}
                    className="inline-flex min-w-0 items-center gap-1 rounded-md border border-border/70 bg-surface-sunken px-1.5 py-0.5 text-2xs text-muted-foreground"
                  >
                    <FileText className="h-3 w-3 shrink-0" aria-hidden="true" />
                    <span className="truncate">{s.filename}</span>
                  </span>
                ))}
              </div>
            </>
          )}
        </div>

        {!editing && (
          <div className="flex shrink-0 flex-wrap items-center gap-1.5 sm:justify-end">
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

            {/* Secondary actions fade in on hover but stay reachable via keyboard. */}
            <div
              className={cn(
                "flex items-center gap-1",
                "opacity-100 transition-opacity duration-200 ease-out-expo",
                "sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100"
              )}
            >
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
          </div>
        )}
      </div>
    </div>
  );
}
