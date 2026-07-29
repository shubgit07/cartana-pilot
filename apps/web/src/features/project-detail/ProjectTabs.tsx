"use client";

import type * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { NavigationTab } from "@/lib/constants";

export type ProjectTabProps = {
  [K in NavigationTab]: React.ReactNode;
};

/** Tab order is the intended left-to-right reading order of the workflow. */
const TABS: ReadonlyArray<{ value: NavigationTab; label: string }> = [
  { value: "overview", label: "Overview" },
  { value: "sources", label: "Sources" },
  { value: "requirements", label: "Requirements" },
  { value: "tasks", label: "Tasks" },
  { value: "chat", label: "Chat" },
  { value: "audit", label: "Audit" },
];

export function ProjectTabs({
  value,
  onValueChange,
  sourceCount,
  panels,
}: {
  value: NavigationTab;
  onValueChange: (next: NavigationTab) => void;
  sourceCount: number;
  panels: ProjectTabProps;
}) {
  return (
    <Tabs
      value={value}
      onValueChange={(v) => onValueChange(v as NavigationTab)}
      className="space-y-4"
    >
      <TabsList
        variant="underline"
        aria-label="Project sections"
        className="scrollbar-thin w-full justify-start gap-1 overflow-x-auto"
      >
        {TABS.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value} className="shrink-0">
            {tab.label}
            {tab.value === "sources" && (
              <span
                className="ml-1.5 rounded-md bg-surface-sunken px-1.5 py-0.5 text-2xs text-muted-foreground tabular"
                aria-hidden="true"
              >
                {sourceCount}
              </span>
            )}
          </TabsTrigger>
        ))}
      </TabsList>

      {TABS.map((tab) => (
        <TabsContent
          key={tab.value}
          value={tab.value}
          tabIndex={-1}
          className="animate-fade-in focus-visible:outline-none"
        >
          {panels[tab.value]}
        </TabsContent>
      ))}
    </Tabs>
  );
}
