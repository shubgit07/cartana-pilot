"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { NavigationTab } from "@/lib/constants";

export type ProjectTabProps = {
  [K in NavigationTab]: React.ReactNode;
};

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
      className="space-y-2"
    >
      <TabsList aria-label="Project sections" className="w-full justify-start gap-1 overflow-x-auto">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="sources">
          Sources <span className="ml-1 tabular text-muted-foreground">({sourceCount})</span>
        </TabsTrigger>
        <TabsTrigger value="requirements">Requirements</TabsTrigger>
        <TabsTrigger value="tasks">Tasks</TabsTrigger>
        <TabsTrigger value="chat">Chat</TabsTrigger>
        <TabsTrigger value="audit">Audit</TabsTrigger>
      </TabsList>

      <TabsContent value="overview" tabIndex={-1}>
        {panels.overview}
      </TabsContent>
      <TabsContent value="sources" tabIndex={-1}>
        {panels.sources}
      </TabsContent>
      <TabsContent value="requirements" tabIndex={-1}>
        {panels.requirements}
      </TabsContent>
      <TabsContent value="tasks" tabIndex={-1}>
        {panels.tasks}
      </TabsContent>
      <TabsContent value="chat" tabIndex={-1}>
        {panels.chat}
      </TabsContent>
      <TabsContent value="audit" tabIndex={-1}>
        {panels.audit}
      </TabsContent>
    </Tabs>
  );
}
