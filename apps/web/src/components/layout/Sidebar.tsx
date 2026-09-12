"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, usePathname, useSearchParams } from "next/navigation";
import {
  ChevronDown,
  FolderGit2,
  Layers,
  ListChecks,
  MessageSquare,
  Plus,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { CartanaLogo } from "./CartanaLogo";
import { ThemeToggle } from "./ThemeToggle";
import { useProject } from "@/hooks/api";
import type { NavigationTab } from "@/lib/constants";
import { cn } from "@/lib/cn";

const PROJECT_TABS: ReadonlyArray<{ value: NavigationTab; label: string; icon: LucideIcon }> = [
  { value: "requirements", label: "Requirements", icon: ListChecks },
  { value: "repository", label: "Repository", icon: FolderGit2 },
  { value: "compliance", label: "Compliance", icon: ShieldCheck },
  { value: "chat", label: "Chat", icon: MessageSquare },
];

function rowClass(active: boolean) {
  return cn(
    "flex h-7 items-center gap-1.5 rounded-lg px-2 text-[13px] font-medium transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    active
      ? "bg-surface-hover text-foreground"
      : "text-muted-foreground hover:bg-surface-hover/60 hover:text-foreground"
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="px-2 text-[12px] font-medium text-muted-foreground">{children}</p>;
}

/** Project section with ?tab= links. useSearchParams needs a Suspense boundary. */
function OpenProjectSection({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const activeTab = (searchParams.get("tab") ?? "requirements") as NavigationTab;
  const { project } = useProject(projectId);

  return (
    <div className="space-y-1">
      <SectionLabel>
        <span className="block truncate">{project?.name ?? "Project"}</span>
      </SectionLabel>
      {PROJECT_TABS.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.value;
        return (
          <Link
            key={tab.value}
            href={`/projects/${projectId}?tab=${tab.value}`}
            aria-current={active ? "page" : undefined}
            className={rowClass(active)}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{tab.label}</span>
          </Link>
        );
      })}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const params = useParams<{ id?: string }>();
  const projectId = params?.id;
  const onHome = pathname === "/";

  return (
    <nav aria-label="Primary" className="flex h-full flex-col gap-1 overflow-y-auto px-1 py-2">
      {/* Workspace row */}
      <div className="flex items-center gap-1 px-1">
        <Link
          href="/"
          className={cn(
            "flex h-8 min-w-0 flex-1 items-center gap-1.5 rounded-lg px-1.5 transition-colors hover:bg-surface-hover",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          )}
        >
          <span className="grid size-5 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground">
            <CartanaLogo className="size-3.5" />
          </span>
          <span className="truncate text-[13px] font-medium tracking-tight text-foreground">
            Cartana
          </span>
          <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
        </Link>
        <Link
          href="/?create=new"
          aria-label="Create new project"
          title="Create new project"
          className={cn(
            "grid size-7 shrink-0 place-items-center rounded-full border border-border text-muted-foreground transition-colors",
            "hover:border-border-strong hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          )}
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>

      {/* Main nav */}
      <div className="space-y-1 pt-2">
        <Link href="/" aria-current={onHome ? "page" : undefined} className={rowClass(onHome)}>
          <Layers className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="truncate">Projects</span>
        </Link>
      </div>

      {/* Workspace section */}
      <div className="space-y-1 pt-3">
        <SectionLabel>Workspace</SectionLabel>
        <Link href="/" aria-current={onHome ? "page" : undefined} className={rowClass(onHome)}>
          <Layers className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="truncate">Projects</span>
        </Link>
      </div>

      {/* Open project */}
      {projectId && (
        <div className="pt-3">
          <React.Suspense
            fallback={
              <div className="space-y-1" aria-hidden="true">
                <div className="h-4 w-2/3 rounded bg-surface-hover" />
                <div className="h-7 rounded-lg bg-surface-hover/60" />
                <div className="h-7 rounded-lg bg-surface-hover/60" />
              </div>
            }
          >
            <OpenProjectSection projectId={projectId} />
          </React.Suspense>
        </div>
      )}

      <div className="mt-auto flex items-center gap-2 px-1 pt-3">
        <ThemeToggle className="h-7 w-7 rounded-full [&_svg]:size-3.5" />
        <span className="truncate text-[11px] text-muted-foreground">Local MVP · No login</span>
      </div>
    </nav>
  );
}
