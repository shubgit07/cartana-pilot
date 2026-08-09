import Link from "next/link";
import { CartanaLogo } from "./CartanaLogo";
import { ThemeToggle } from "./ThemeToggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full flex-col bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/65 safe-px safe-pt">
        <div className="container flex h-14 items-center justify-between gap-4">
          <Link
            href="/"
            className="group -ml-1.5 inline-flex items-center gap-2.5 rounded-md px-1.5 py-1 transition-colors duration-150 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <span className="grid size-7 place-items-center rounded-md bg-primary-soft text-primary-soft-foreground transition-colors duration-150">
              <CartanaLogo className="size-[1.3rem]" />
            </span>
            <span
              className="font-serif text-[1.21875rem] font-semibold tracking-tight text-foreground"
              translate="no"
            >
              Cartana
            </span>
          </Link>

          <nav aria-label="Utilities" className="flex items-center gap-2">
            <span className="hidden text-xs text-muted-foreground sm:inline">
              Your PR copilot
            </span>
            <span aria-hidden="true" className="hidden h-4 w-px bg-border sm:inline-block" />
            <ThemeToggle />
          </nav>
        </div>
      </header>

      <main id="main-content" tabIndex={-1} className="container flex-1 py-8 safe-px">
        {children}
      </main>

      <footer className="border-t border-border/70 safe-px safe-pb">
        <div className="container flex flex-wrap items-center gap-x-2 gap-y-1 py-5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground/70">Cartana</span>
          <span aria-hidden="true">·</span>
          <span>Single-user local MVP</span>
          <span aria-hidden="true">·</span>
          <span>Phase 1</span>
          <span aria-hidden="true">·</span>
          <span>No login</span>
        </div>
      </footer>
    </div>
  );
}
