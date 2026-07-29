"use client";

import * as React from "react";
import { ArrowRight, Check, FileText, Loader2, Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { TaskStateBadge } from "./TaskStateBadge";
import { TaskEditForm } from "./TaskEditForm";
import type { TaskSummary } from "@cartana/shared";

type Props = {
  task: TaskSummary;
  linkableRequirements: { id: string; title: string }[];
  onAccept: () => void;
  onReject: () => void;
  onSave: (patch: {
    title?: string;
    description?: string | null;
    requirementId?: string | null;
  }) => Promise<void>;
  onDelete: () => void;
};

/** Left rail colour per task state, resolved through theme tokens. */
const STATE_RAIL: Record<string, string> = {
  accepted: "bg-success",
  edited: "bg-warning",
  suggested: "bg-info",
  rejected: "bg-border-strong",
};

export function TaskRow({ task: t, linkableRequirements, onAccept, onReject, onSave, onDelete }: Props) {
  const [editing, setEditing] = React.useState(false);
  const [pending, setPending] = React.useState<"accept" | "reject" | null>(null);
  const isDecided = t.state === "accepted" || t.state === "rejected";
  const isHidden = t.state === "rejected";

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
        className={cn("absolute inset-y-0 left-0 w-1", STATE_RAIL[t.state] ?? "bg-border-strong")}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          {editing ? (
            <TaskEditForm
              initialTitle={t.title}
              initialDescription={t.description}
              initialRequirementId={t.requirementId}
              linkableRequirements={linkableRequirements}
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
                {t.title}
              </h3>

              {t.description && (
                <p className="mt-1 break-words text-sm leading-relaxed text-muted-foreground">
                  {t.description}
                </p>
              )}

              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <TaskStateBadge state={t.state} origin={t.origin} />

                {t.requirementTitle && (
                  <span className="inline-flex min-w-0 items-center gap-1 rounded-md border border-primary/20 bg-primary-soft px-1.5 py-0.5 text-2xs text-primary-soft-foreground">
                    <ArrowRight className="h-3 w-3 shrink-0" aria-hidden="true" />
                    <span className="truncate">{t.requirementTitle}</span>
                  </span>
                )}

                {t.sourceLinks.map((s) => (
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
                  aria-label={`Accept task "${t.title}"`}
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
                  aria-label={`Reject task "${t.title}"`}
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
                aria-label={`Edit task "${t.title}"`}
              >
                <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={onDelete}
                aria-label={`Delete task "${t.title}"`}
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
