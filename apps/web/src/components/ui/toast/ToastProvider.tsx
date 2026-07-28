"use client";

import * as React from "react";
import { cn } from "@/lib/cn";
import { VISUALLY_HIDDEN_CLASS } from "@/lib/aria";
import { TOAST_DURATION_MS } from "@/lib/constants";

export type ToastVariant = "default" | "destructive";

export type ToastInput = {
  title?: string;
  description?: string;
  variant?: ToastVariant;
  durationMs?: number;
};

type Toast = {
  id: string;
  createdAt: number;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  durationMs?: number;
};

type ToastContextValue = {
  toast: (t: ToastInput) => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const toast = React.useCallback((t: ToastInput) => {
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2);
    const createdAt = Date.now();
    const next: Toast = { ...t, id, createdAt };
    setToasts((prev) => [...prev, next]);
    const duration = t.durationMs ?? TOAST_DURATION_MS;
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, duration);
  }, []);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex w-full flex-col items-center gap-2 px-4 safe-pb sm:left-auto sm:right-4 sm:items-end sm:px-0">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="flex w-full max-w-sm flex-col gap-2"
      >
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onDismiss={onDismiss} />
        ))}
      </div>
    </div>
  );
}

function ToastCard({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  const isDestructive = toast.variant === "destructive";

  return (
    <div
      className={cn(
        "pointer-events-auto relative overflow-hidden rounded-lg border border-border",
        "bg-popover/95 p-3.5 pl-4 text-popover-foreground shadow-overlay backdrop-blur-sm",
        "animate-slide-up",
        isDestructive && "border-danger/40"
      )}
    >
      {/* Accent rail — carries the semantic colour without tinting the whole surface. */}
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-y-0 left-0 w-[3px]",
          isDestructive ? "bg-danger" : "bg-primary"
        )}
      />
      <div className="flex items-start gap-3">
        <div className="flex-1 space-y-0.5">
          {toast.title && (
            <div className="text-sm font-medium leading-snug tracking-tight">{toast.title}</div>
          )}
          {toast.description && (
            <div className="text-xs leading-relaxed text-muted-foreground">{toast.description}</div>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss notification"
          className={cn(
            "-m-1 grid size-7 shrink-0 place-items-center rounded-md text-muted-foreground",
            "transition-colors duration-150 hover:bg-surface-hover hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-popover"
          )}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>
      <span className={VISUALLY_HIDDEN_CLASS}>
        {toast.title ?? "Notification"}
        {isDestructive ? " (error)" : ""}
      </span>
    </div>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
