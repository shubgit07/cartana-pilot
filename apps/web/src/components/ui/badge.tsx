import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const badgeVariants = cva(
  cn(
    "inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5",
    "text-2xs font-semibold uppercase leading-4 tracking-[0.04em]",
    "transition-colors duration-150",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
  ),
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-border bg-surface text-muted-foreground",
        outline: "border-border text-foreground",
        muted: "border-transparent bg-muted text-muted-foreground",
        // Semantic tones resolve through theme tokens.
        success: "border-transparent bg-success-soft text-success-soft-foreground",
        warning: "border-transparent bg-warning-soft text-warning-soft-foreground",
        info: "border-transparent bg-info-soft text-info-soft-foreground",
        danger: "border-transparent bg-danger-soft text-danger-soft-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

/** Dot colours keyed to the badge variant, for the optional status indicator. */
const DOT_CLASS: Record<string, string> = {
  default: "bg-primary-foreground/70",
  secondary: "bg-accent-foreground/50",
  outline: "bg-muted-foreground",
  muted: "bg-muted-foreground",
  success: "bg-success",
  warning: "bg-warning",
  info: "bg-info",
  danger: "bg-danger",
};

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  /** Renders a small leading status dot. Decorative only. */
  dot?: boolean;
}

export function Badge({ className, variant, dot = false, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          aria-hidden="true"
          className={cn("size-1.5 shrink-0 rounded-full", DOT_CLASS[variant ?? "default"])}
        />
      )}
      {children}
    </span>
  );
}

export { badgeVariants };
