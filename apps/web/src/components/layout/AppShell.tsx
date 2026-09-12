"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { SkipLink } from "./SkipLink";
import { CartanaLogo } from "./CartanaLogo";
import { cn } from "@/lib/cn";

/**
 * Linear app shell: fixed 244px sidebar + inset main panel (rounded frame
 * with a hairline border). No top header / footer chrome — navigation lives
 * in the sidebar. Mobile gets a menu button + slide-over sidebar.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <div className="flex h-dvh gap-2 bg-background p-2 text-foreground">
      <SkipLink href="#main-content">Skip to main content</SkipLink>

      {/* Desktop sidebar */}
      <aside className="hidden w-[244px] shrink-0 md:block" aria-label="Sidebar">
        <Sidebar />
      </aside>

      {/* Mobile slide-over */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 cursor-default bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-[244px] bg-background p-2">
            <Sidebar />
          </div>
        </div>
      )}

      {/* Main panel */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-surface">
        {/* Mobile bar */}
        <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3 md:hidden">
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
            className={cn(
              "grid size-7 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-hover hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70"
            )}
          >
            {mobileOpen ? (
              <X className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Menu className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
          <Link href="/" className="flex items-center gap-1.5" aria-label="Cartana home">
            <span className="grid size-5 place-items-center rounded-md bg-primary text-primary-foreground">
              <CartanaLogo className="size-3.5" />
            </span>
            <span className="text-[13px] font-medium tracking-tight">Cartana</span>
          </Link>
        </div>

        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-0 flex-1 overflow-y-auto focus-visible:outline-none"
        >
          <div className="mx-auto w-full max-w-[1200px] px-4 py-4 sm:px-5">{children}</div>
        </main>
      </div>
    </div>
  );
}
