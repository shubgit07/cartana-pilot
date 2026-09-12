"use client";

import * as React from "react";
import {
  GitPullRequest,
  History,
  ShieldCheck,
} from "lucide-react";
import { PRTrustBriefDashboard } from "../audit/PRTrustBriefDashboard";
import { ReadinessView } from "./ReadinessView";
import { PreviousRunsView } from "./PreviousRunsView";
import { cn } from "@/lib/cn";

type Props = {
  projectId: string;
};

type ComplianceSubTab = "verification" | "readiness" | "runs";

const COMPLIANCE_SUB_TABS: ReadonlyArray<{
  value: ComplianceSubTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { value: "verification", label: "PR Verification & Report", icon: GitPullRequest },
  { value: "readiness", label: "Spec Readiness", icon: ShieldCheck },
  { value: "runs", label: "Previous Runs", icon: History },
];

export function CompliancePanel({ projectId }: Props) {
  const [activeTab, setActiveTab] = React.useState<ComplianceSubTab>("verification");
  const [selectedBrief, setSelectedBrief] = React.useState<
    import("@cartana/shared").PRTrustBrief | null
  >(null);

  return (
    <div className="space-y-6">
      {/* Linear-style Pill Sub-Navigation inside Compliance */}
      <div className="flex items-center justify-between border-b border-border/70 pb-3">
        <nav
          className="flex items-center gap-1.5 overflow-x-auto scrollbar-thin"
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
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors shrink-0",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70",
                  isActive
                    ? "bg-surface-sunken text-foreground border border-border shadow-xs"
                    : "text-muted-foreground hover:bg-surface-hover hover:text-foreground"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Sub-View Content */}
      <div className="animate-fade-in">
        {activeTab === "verification" && (
          <section aria-label="PR Verification and Evidence Report">
            <PRTrustBriefDashboard projectId={projectId} externalBrief={selectedBrief} />
          </section>
        )}

        {activeTab === "readiness" && (
          <section aria-label="Pre-Implementation Spec Readiness">
            <ReadinessView projectId={projectId} />
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
