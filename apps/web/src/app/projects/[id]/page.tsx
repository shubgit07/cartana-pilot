"use client";

import { ProjectDetailPage } from "@/features/project-detail";
import { SourcesPanel } from "@/features/sources";
import { RequirementsPanel } from "@/features/requirements";
import { TasksPanel } from "@/features/tasks";
import { ChatPanel } from "@/features/chat";
import { AuditPanel } from "@/features/audit";

export default function Page() {
  return (
    <ProjectDetailPage
      panels={{
        sources: <SourcesById />,
        requirements: <RequirementsById />,
        tasks: <TasksById />,
        chat: <ChatById />,
        audit: <AuditById />,
      }}
    />
  );
}

// Small adapters — the panel components bind the projectId resolved by
// ProjectDetailPage's useParams() when they mount. We use a thin wrapper
// that calls a child component to forward the id. To keep this lean, we
// use a client component that reads useParams.

import { ReadId } from "./read-id";

function SourcesById() {
  return (
    <ReadId>
      {(id) => <SourcesPanel projectId={id} />}
    </ReadId>
  );
}
function RequirementsById() {
  return (
    <ReadId>
      {(id) => <RequirementsPanel projectId={id} />}
    </ReadId>
  );
}
function TasksById() {
  return (
    <ReadId>
      {(id) => <TasksPanel projectId={id} />}
    </ReadId>
  );
}
function ChatById() {
  return (
    <ReadId>
      {(id) => <ChatPanel projectId={id} />}
    </ReadId>
  );
}
function AuditById() {
  return (
    <ReadId>
      {(id) => <AuditPanel projectId={id} />}
    </ReadId>
  );
}
