"use client";

import * as React from "react";
import { AlertTriangle, FileQuestion, Inbox } from "lucide-react";
import { cn } from "@/lib/cn";

type IconKind = "alert" | "search" | "inbox" | "none";

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
  icon?: IconKind;
  className?: string;
  children?: React.ReactNode;
}) {
  const Icon = icon === "alert" ? AlertTriangle : icon === "search" ? FileQuestion : icon === "inbox" ? Inbox : null;
  return (
    <div
      role={icon === "alert" ? "alert" : undefined}
      className={cn(
        "mx-auto flex max-w-md flex-col items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-10 text-center",
        className
      )}
    >
      {Icon && (
        <Icon
          className="h-6 w-6 text-muted-foreground"
          aria-hidden="true"
        />
      )}
      <div className="space-y-1">
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="mt-2 flex flex-wrap items-center justify-center gap-2">{actions}</div>}
      {children}
    </div>
  );
}
