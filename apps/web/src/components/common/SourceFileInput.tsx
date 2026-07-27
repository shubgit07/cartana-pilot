"use client";

import * as React from "react";
import { UploadCloud, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

type Props = {
  accept?: string;
  disabled?: boolean;
  loading?: boolean;
  onFile: (file: File) => void | Promise<void>;
  label?: string;
  className?: string;
  id?: string;
};

const DEFAULT_ACCEPT = ".pdf,.txt,.md,application/pdf,text/plain,text/markdown";

export function SourceFileInput({
  accept = DEFAULT_ACCEPT,
  disabled,
  loading,
  onFile,
  label = "Upload file",
  className,
  id = "source-file-input",
}: Props) {
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const [internalLoading, setInternalLoading] = React.useState(false);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setInternalLoading(true);
    try {
      await onFile(file);
    } finally {
      setInternalLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const busy = loading || internalLoading;

  return (
    <>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || busy}
        className={cn(
          "inline-flex h-9 items-center gap-2 rounded-md border bg-background px-3 text-sm font-medium transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          className
        )}
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <UploadCloud className="h-4 w-4" aria-hidden="true" />
        )}
        {busy ? "Uploading…" : label}
      </button>
      <label htmlFor={id} className="sr-only">
        Choose source file to upload
      </label>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={handleChange}
        disabled={disabled || busy}
        aria-label="Source file"
      />
    </>
  );
}
