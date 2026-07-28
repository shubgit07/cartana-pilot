"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

type TabsVariant = "underline" | "pill";

/**
 * Lets `TabsList` set the visual variant once; triggers read it from context
 * so callers never have to repeat the prop on every tab.
 */
const TabsVariantContext = React.createContext<TabsVariant>("underline");

export const Tabs = TabsPrimitive.Root;

export interface TabsListProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> {
  variant?: TabsVariant;
}

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  TabsListProps
>(({ className, variant = "underline", ...props }, ref) => (
  <TabsVariantContext.Provider value={variant}>
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "inline-flex items-center text-muted-foreground",
        variant === "underline" && "h-10 justify-start gap-1 border-b border-border",
        variant === "pill" &&
          "h-9 justify-start gap-1 rounded-lg border border-border bg-surface-sunken p-1",
        className
      )}
      {...props}
    />
  </TabsVariantContext.Provider>
));
TabsList.displayName = TabsPrimitive.List.displayName;

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => {
  const variant = React.useContext(TabsVariantContext);

  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium",
        "transition-[background-color,color,border-color,box-shadow] duration-150 ease-out-expo",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        variant === "underline" && [
          "-mb-px border-b-2 border-transparent px-3 py-2",
          "hover:text-foreground",
          "data-[state=active]:border-primary data-[state=active]:text-foreground",
        ],
        variant === "pill" && [
          "rounded-md px-3 py-1",
          "hover:text-foreground",
          "data-[state=active]:bg-surface data-[state=active]:text-foreground data-[state=active]:shadow-soft",
        ],
        className
      )}
      {...props}
    />
  );
});
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

export const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      "data-[state=active]:animate-fade-in",
      className
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;
