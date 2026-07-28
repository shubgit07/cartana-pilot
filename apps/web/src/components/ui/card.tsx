import * as React from "react";
import { cn } from "@/lib/cn";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Adds hover elevation + border emphasis. Use for clickable cards. */
  interactive?: boolean;
  /** Surface treatment. "sunken" recedes; "plain" drops the border entirely. */
  tone?: "default" | "sunken" | "plain";
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, interactive = false, tone = "default", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-lg text-card-foreground",
        "transition-[background-color,border-color,box-shadow] duration-200 ease-out-expo",
        tone === "default" && "border border-border bg-card shadow-card",
        tone === "sunken" && "border border-border/70 bg-surface-sunken",
        tone === "plain" && "bg-card",
        interactive &&
          "cursor-pointer hover:border-border-strong hover:bg-surface-hover hover:shadow-raised",
        className
      )}
      {...props}
    />
  )
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-5", className)} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("text-base font-semibold leading-tight tracking-tight", className)}
      {...props}
    />
  )
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn("text-sm leading-relaxed text-muted-foreground", className)} {...props} />
));
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-5 pt-0", className)} {...props} />
  )
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center gap-2 p-5 pt-0", className)} {...props} />
  )
);
CardFooter.displayName = "CardFooter";
