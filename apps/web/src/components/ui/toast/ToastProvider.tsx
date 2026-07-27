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
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex w-full flex-col items-center gap-2 px-4 sm:items-end sm:right-4 sm:left-auto sm:px-0">
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
  return (
    <div
      className={cn(
        "pointer-events-auto rounded-md border bg-card p-3 text-card-foreground shadow-md",
        toast.variant === "destructive" && "border-destructive/40 bg-destructive/5"
      )}
    >
      <div className="flex items-start gap-2">
        <div className="flex-1">
          {toast.title && <div className="text-sm font-medium">{toast.title}</div>}
          {toast.description && (
            <div className="mt-0.5 text-xs text-muted-foreground">{toast.description}</div>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss notification"
          className="-m-1 grid h-7 w-7 place-items-center rounded text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>
      <span className={VISUALLY_HIDDEN_CLASS}>
        {toast.title ?? "Notification"}
        {toast.variant === "destructive" ? " (error)" : ""}
      </span>
    </div>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
