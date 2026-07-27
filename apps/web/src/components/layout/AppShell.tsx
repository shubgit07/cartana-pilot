import Link from "next/link";
import { CartanaLogo } from "./CartanaLogo";
import { ThemeToggle } from "./ThemeToggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full flex-col bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 safe-px safe-pt">
        <div className="container flex h-14 items-center justify-between gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 font-semibold tracking-tight text-foreground transition-colors hover:text-foreground/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <CartanaLogo className="h-5 w-5" />
            <span translate="no">Cartana</span>
          </Link>
          <nav className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="hidden sm:inline">Project specification copilot</span>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="container py-8 safe-px">
        {children}
      </main>
      <footer className="container safe-px border-t py-6 text-xs text-muted-foreground">
        <span>
          Single-user local MVP ·{" "}
          <span className="font-medium text-foreground/70">Phase 1</span> · no login
        </span>
      </footer>
    </div>
  );
}
