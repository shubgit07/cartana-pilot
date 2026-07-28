import * as React from "react";
import { cn } from "@/lib/cn";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-input bg-surface px-3 py-1 text-sm text-foreground shadow-soft",
        "transition-[background-color,border-color,box-shadow] duration-150 ease-out-expo",
        "placeholder:text-muted-foreground/80",
        "hover:border-border-strong",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        "focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25 focus-visible:ring-offset-0",
        "aria-[invalid=true]:border-danger aria-[invalid=true]:focus-visible:ring-danger/25",
        "disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
