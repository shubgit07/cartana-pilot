import * as React from "react";
import { cn } from "@/lib/cn";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-input bg-surface px-3 py-2 text-sm leading-relaxed text-foreground shadow-soft",
        "transition-[background-color,border-color,box-shadow] duration-150 ease-out-expo",
        "placeholder:text-muted-foreground/80",
        "hover:border-border-strong",
        "focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25 focus-visible:ring-offset-0",
        "aria-[invalid=true]:border-danger aria-[invalid=true]:focus-visible:ring-danger/25",
        "disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";
