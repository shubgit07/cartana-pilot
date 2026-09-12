"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

/**
 * Linear app language (from the project-exports): pill buttons, lavender
 * primary with lighter hover + focus-tinted press, charcoal secondary
 * carried by a 1px hairline. Marketing-doc 8px radii do NOT apply here —
 * the real app UI is pill everywhere.
 */
const buttonVariants = cva(
  cn(
    "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-full",
    "text-sm font-medium leading-none",
    // Micro-interactions: colour, border, and elevation animate; transform gives press feedback.
    "transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-out-expo",
    "active:translate-y-px",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0"
  ),
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-soft hover:bg-primary-hover active:bg-primary-focus",
        secondary:
          "border border-border bg-surface text-foreground hover:border-border-strong hover:bg-surface-hover",
        /** Tinted lavender fill for low-emphasis actions on dark. */
        soft:
          "bg-primary-soft text-primary-soft-foreground hover:bg-primary-soft/70",
        outline:
          "border border-border bg-surface text-foreground shadow-soft hover:border-border-strong hover:bg-surface-hover",
        ghost:
          "text-muted-foreground hover:bg-surface-hover hover:text-foreground",
        destructive:
          "bg-destructive text-destructive-foreground shadow-soft hover:bg-destructive/90",
        link:
          "text-primary underline-offset-4 hover:underline active:translate-y-0",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-6",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";

export { buttonVariants };
