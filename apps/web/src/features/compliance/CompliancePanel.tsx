"use client";

import * as React from "react";
import { GitPullRequest, History } from "lucide-react";
import { PRTrustBriefDashboard } from "../audit/PRTrustBriefDashboard";
import { PreviousRunsView } from "./PreviousRunsView";
import { cn } from "@/lib/cn";
import type { PRTrustBrief } from "@cartana/shared";

type Props = {
  projectId: string;
};

type ComplianceSubTab = "verification" | "runs";

const COMPLIANCE_SUB_TABS: ReadonlyArray<{
  value: ComplianceSubTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { value: "verification", label: "PR verification", icon: GitPullRequest },
  { value: "runs", label: "Previous runs", icon: History },
];

export function CompliancePanel({ projectId }: Props) {
  const [activeTab, setActiveTab] = React.useState<ComplianceSubTab>("verification");
  const [selectedBrief, setSelectedBrief] = React.useState<PRTrustBrief | null>(null);

  return (
    <div className="space-y-6">
      {/* Underline sub-navigation: uppercase micro-labels on a hairline rule */}
      <nav
        className="flex items-center gap-1 overflow-x-auto border-b border-border scrollbar-thin"
        aria-label="Compliance sub-sections"
      >
        {COMPLIANCE_SUB_TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.value;
          return (
            <button
              key={tab.value}
              type="button"
              onClick={() => setActiveTab(tab.value)}
              className={cn(
                "-mb-px flex shrink-0 items-center gap-1.5 border-b-2 border-transparent px-3 py-2 text-2xs font-semibold uppercase tracking-[0.04em] transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70",
                isActive
                  ? "border-primary text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Sub-View Content */}
      <div className="animate-fade-in">
        {activeTab === "verification" && (
          <section aria-label="PR Verification and Evidence Report">
            <PRTrustBriefDashboard projectId={projectId} externalBrief={selectedBrief} />
          </section>
        )}

        {activeTab === "runs" && (
          <section aria-label="Historical Verification Runs">
            <PreviousRunsView
              projectId={projectId}
              onSelectRun={(brief) => {
                setSelectedBrief(brief);
                setActiveTab("verification");
              }}
            />
          </section>
        )}
      </div>
    </div>
  );
}
