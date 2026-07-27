"use client";

import * as React from "react";
import { Check, FileText, Loader2, Pencil, Trash2, X } from "lucide-react";
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

export function TaskRow({ task: t, linkableRequirements, onAccept, onReject, onSave, onDelete }: Props) {
  const [editing, setEditing] = React.useState(false);
  const [pending, setPending] = React.useState<"accept" | "reject" | null>(null);
  const isDecided = t.state === "accepted" || t.state === "rejected";

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
    <div className={cn(t.state === "rejected" && "opacity-60")}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
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
              <h3 className="text-sm font-medium">{t.title}</h3>
              {t.description && (
                <p className="mt-1 text-sm break-words text-muted-foreground">{t.description}</p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <TaskStateBadge state={t.state} origin={t.origin} />
                {t.requirementTitle && (
                  <span className="rounded bg-accent px-1.5 py-0.5 text-accent-foreground">
                    <span aria-hidden="true">→ </span>
                    {t.requirementTitle}
                  </span>
                )}
                {t.sourceLinks.length > 0 && (
                  <span className="inline-flex items-center gap-1">
                    <FileText className="h-3 w-3" aria-hidden="true" />
                    {t.sourceLinks.map((s) => s.filename).join(", ")}
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
        )}
      </div>
    </div>
  );
}
