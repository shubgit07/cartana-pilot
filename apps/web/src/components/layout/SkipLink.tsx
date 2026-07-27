import Link from "next/link";

export function SkipLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="sr-only absolute left-2 top-2 z-50 rounded-md bg-foreground px-3 py-2 text-sm text-background focus:not-sr-only focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
    >
      {children}
    </Link>
  );
}
