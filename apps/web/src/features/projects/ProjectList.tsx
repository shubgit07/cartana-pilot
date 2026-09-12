"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Boxes, Plus, Search } from "lucide-react";
import { useProjects } from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { VISUALLY_HIDDEN_CLASS } from "@/lib/aria";
import { CreateProjectDialog } from "./CreateProjectDialog";
import { ProjectRow } from "./ProjectRow";
import { cn } from "@/lib/cn";

const ErrorHint = ({ message }: { message: string }) => (
  <div className="space-y-1">
    <p className="font-medium">{message}</p>
    <p className="text-xs opacity-90">
      Make sure the API is running (<code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code>) and
      Postgres + Redis are up (<code className="font-mono">npm run infra:up</code>).
    </p>
  </div>
);

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-primary-foreground/40 px-1 py-px font-mono text-[10px] leading-none">
      {children}
    </kbd>
  );
}

export function ProjectList() {
  const { projects, loading, error, reload } = useProjects();
  const { toast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();
  const createOpen = searchParams.get("create") === "new";

  const [query, setQuery] = React.useState("");
  const [selected, setSelected] = React.useState<ReadonlySet<string>>(new Set());

  const closeComposer = React.useCallback(() => {
    router.replace("/", { scroll: false });
  }, [router]);

  // Linear shortcut: N then P opens the composer (ignored while typing).
  React.useEffect(() => {
    let armedAt = 0;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) {
        return;
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const now = Date.now();
      if (e.key.toLowerCase() === "n") {
        armedAt = now;
      } else if (e.key.toLowerCase() === "p" && now - armedAt < 800) {
        armedAt = 0;
        e.preventDefault();
        router.push("/?create=new", { scroll: false });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  // Reset selection whenever the list itself changes.
  React.useEffect(() => {
    setSelected(new Set());
  }, [projects]);

  const toggle = React.useCallback((id: string, next: boolean) => {
    setSelected((prev) => {
      const copy = new Set(prev);
      if (next) copy.add(id);
      else copy.delete(id);
      return copy;
    });
  }, []);

  const allIds = React.useMemo(() => (projects ?? []).map((p) => p.id), [projects]);
  const allSelected = allIds.length > 0 && selected.size === allIds.length;
  const toggleAll = React.useCallback(
    (next: boolean) => setSelected(next ? new Set(allIds) : new Set()),
    [allIds]
  );

  const visible = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return projects ?? [];
    return (projects ?? []).filter(
      (p) =>
        p.name.toLowerCase().includes(q) || (p.description ?? "").toLowerCase().includes(q)
    );
  }, [projects, query]);

  const count = projects?.length ?? 0;

  return (
    <div className="animate-fade-in">
      {/* Header bar */}
      <header className="border-b border-border">
        <div className="flex min-h-[43px] items-center justify-between gap-2">
          <h1 className="px-2.5 text-[13px] font-medium text-foreground">Projects</h1>
          <Button asChild size="sm" className="my-1.5">
            <Link href="/?create=new">
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              New project
            </Link>
          </Button>
        </div>
        <div className="flex min-h-[43px] items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="rounded-full bg-surface-hover px-2.5 py-1 text-xs font-medium text-foreground">
              All projects
            </span>
            {selected.size > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="tabular">{selected.size} selected</span>
                <button
                  type="button"
                  onClick={() => setSelected(new Set())}
                  className="rounded-full px-1.5 py-0.5 transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70"
                >
                  Clear
                </button>
              </span>
            )}
          </div>
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="search"
              name="project-filter"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter projects…"
              aria-label="Filter projects"
              autoComplete="off"
              spellCheck={false}
              className="h-7 w-44 rounded-full pl-8 text-xs sm:w-52"
            />
          </div>
        </div>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-xl border border-danger/25 bg-danger-soft p-3 text-sm text-danger-soft-foreground"
        >
          <ErrorHint message={error} />
        </div>
      )}

      {loading && <ProjectsTableSkeleton />}

      {!loading && !error && count === 0 && (
        <div className="flex flex-col items-center px-6 py-16 text-center">
          <Boxes
            className="h-20 w-20 text-muted-foreground"
            strokeWidth={1}
            aria-hidden="true"
          />
          <h2 className="mt-6 text-[15px] font-semibold text-foreground">Projects</h2>
          <p className="mt-2 max-w-md text-[13px] leading-relaxed text-muted-foreground">
            Projects hold your spec documents. Upload sources, extract requirements and tasks,
            then verify every pull request against them before you merge.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            <Button asChild>
              <Link href="/?create=new">
                Create new project
                <span className="ml-1 flex items-center gap-1" aria-hidden="true">
                  <Kbd>N</Kbd>
                  <span className="text-[10px] opacity-80">then</span>
                  <Kbd>P</Kbd>
                </span>
              </Link>
            </Button>
          </div>
        </div>
      )}

      {!loading && !error && count > 0 && (
        <div className="mt-2 overflow-hidden rounded-xl border border-border">
        <table className="w-full border-collapse text-left">
          <caption className={VISUALLY_HIDDEN_CLASS}>All projects</caption>
          <thead>
            <tr className="text-xs font-medium text-muted-foreground">
              <th scope="col" className="w-9 py-2 pl-3 pr-0">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={(e) => toggleAll(e.target.checked)}
                  aria-label="Select all projects"
                  className="block size-3.5 cursor-pointer accent-primary"
                />
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Name
              </th>
              <th scope="col" className="hidden px-2 py-2 font-medium sm:table-cell">
                Sources
              </th>
              <th scope="col" className="hidden px-2 py-2 font-medium md:table-cell">
                Created
              </th>
              <th scope="col" className="px-2 py-2 pr-3 text-right font-medium">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-surface">
            {visible.map((p) => (
              <ProjectRow
                key={p.id}
                project={p}
                selected={selected.has(p.id)}
                onToggle={toggle}
              />
            ))}
          </tbody>
        </table>
        </div>
      )}

      {!loading && !error && count > 0 && visible.length === 0 && (
        <p className="px-2 py-10 text-center text-sm text-muted-foreground" role="status">
          No projects match <q className="text-foreground">{query.trim()}</q>.
        </p>
      )}

      <CreateProjectDialog
        open={createOpen}
        onOpenChange={(next) => {
          if (!next) closeComposer();
        }}
        onCreated={(project) => {
          closeComposer();
          toast({
            title: "Project created",
            description: project.name,
            action: { label: "View project", href: `/projects/${project.id}` },
          });
          void reload();
        }}
      />
    </div>
  );
}

function ProjectsTableSkeleton() {
  return (
    <div className="mt-2 space-y-1.5" aria-busy="true" aria-label="Loading projects">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className={cn("h-11 animate-pulse rounded-lg bg-surface-hover/60")}
          style={{ animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}
