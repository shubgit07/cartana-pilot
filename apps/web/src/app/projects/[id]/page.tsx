"use client";

import { ProjectDetailPage } from "@/features/project-detail";
import { RequirementsPanel } from "@/features/requirements";
import { RepositoryPanel } from "@/features/repository";
import { CompliancePanel } from "@/features/compliance";
import { ChatComingSoon } from "@/features/chat";
import { ReadId } from "./read-id";

export default function Page() {
  return (
    <ProjectDetailPage
      panels={{
        requirements: <RequirementsById />,
        repository: <RepositoryById />,
        compliance: <ComplianceById />,
        chat: <ChatById />,
      }}
    />
  );
}

// Small adapters — the panel components bind the projectId resolved by
// ProjectDetailPage's useParams() when they mount.

function RequirementsById() {
  return (
    <ReadId>
      {(id) => <RequirementsPanel projectId={id} />}
    </ReadId>
  );
}

function RepositoryById() {
  return (
    <ReadId>
      {(id) => <RepositoryPanel projectId={id} />}
    </ReadId>
  );
}

function ComplianceById() {
  return (
    <ReadId>
      {(id) => <CompliancePanel projectId={id} />}
    </ReadId>
  );
}

function ChatById() {
  return <ChatComingSoon />;
}
