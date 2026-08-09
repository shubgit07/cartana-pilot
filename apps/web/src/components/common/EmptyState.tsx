"use client";

import * as React from "react";
import { AlertTriangle, FileQuestion, Inbox } from "lucide-react";
import { cn } from "@/lib/cn";

type IconKind = "alert" | "search" | "inbox" | "none";

const ICONS = {
  alert: AlertTriangle,
  search: FileQuestion,
  inbox: Inbox,
} as const;

/** Icon tile tone per kind — alerts read warm, everything else stays neutral. */
const TILE_TONE: Record<Exclude<IconKind, "none">, string> = {
  alert: "border-danger/25 bg-danger-soft text-danger-soft-foreground",
  search: "border-border bg-surface text-muted-foreground",
  inbox: "border-border bg-surface text-muted-foreground",
};

export function EmptyState({
  title,
  description,
  actions,
  icon = "inbox",
  className,
  children,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  icon?: IconKind | React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}) {
  const iconIsKind = typeof icon === "string";
  const isCustom = !iconIsKind;
  const kind = iconIsKind ? (icon as IconKind) : "inbox";
  const Icon = kind === "none" ? null : ICONS[kind];
  const tileTone = isCustom
    ? "bg-primary-soft text-primary-soft-foreground"
    : kind === "none"
      ? null
      : TILE_TONE[kind];
  const showTile = iconIsKind ? kind !== "none" : Boolean(icon);

  return (
    <div
      role={icon === "alert" ? "alert" : undefined}
      className={cn(
        "relative isolate mx-auto flex max-w-2xl flex-col items-center gap-5 overflow-hidden",
        "rounded-xl border border-dashed border-border bg-card px-10 py-16 text-center",
        "animate-fade-in",
        className
      )}
    >
      {/* Layered backdrop: dotted texture faded out by a soft radial wash. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 texture-dots opacity-40 [mask-image:radial-gradient(70%_60%_at_50%_35%,black,transparent)]"
      />
      <span aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 wash-primary" />

      {showTile && (
        <span
          aria-hidden="true"
          className={cn(
            "grid size-12 place-items-center rounded-xl shadow-soft",
            !isCustom && "border",
            tileTone
          )}
        >
          {iconIsKind && Icon ? <Icon className="size-5" /> : icon}
        </span>
      )}

      <div className="space-y-1.5">
        <h2 className="font-serif text-xl font-semibold tracking-tight text-foreground">{title}</h2>
        {description && (
          <p className="mx-auto max-w-xl text-base leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>



      {actions && (
        <div className="flex flex-wrap items-center justify-center gap-2">{actions}</div>
      )}
      {children}
    </div>
  );
}
