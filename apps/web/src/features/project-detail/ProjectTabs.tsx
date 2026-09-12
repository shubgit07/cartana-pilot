"use client";

import type * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { NavigationTab } from "@/lib/constants";

export type ProjectTabProps = {
  [K in NavigationTab]: React.ReactNode;
};

/** Tab order is the focused left-to-right workflow: Requirements -> Repository -> Compliance -> Chat */
const TABS: ReadonlyArray<{ value: NavigationTab; label: string }> = [
  { value: "requirements", label: "Requirements" },
  { value: "repository", label: "Repository" },
  { value: "compliance", label: "Compliance" },
  { value: "chat", label: "Chat" },
];

export function ProjectTabs({
  value,
  onValueChange,
  panels,
}: {
  value: NavigationTab;
  onValueChange: (next: NavigationTab) => void;
  panels: ProjectTabProps;
}) {
  return (
    <Tabs
      value={value}
      onValueChange={(v) => onValueChange(v as NavigationTab)}
      className="space-y-4"
    >
      {/* Linear-style pill sub-tabs */}
      <TabsList
        variant="pill"
        aria-label="Project sections"
        className="scrollbar-thin w-full justify-start gap-1 overflow-x-auto"
      >
        {TABS.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value} className="shrink-0">
            {tab.label}
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
