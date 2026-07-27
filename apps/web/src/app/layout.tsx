import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/ui/toast";
import { ThemeProvider, themeScript } from "@/lib/theme";
import { SkipLink } from "@/components/layout/SkipLink";

export const metadata: Metadata = {
  title: "Cartana — Project Specification Copilot",
  description: "Turn project documents into a clear execution plan.",
  applicationName: "Cartana",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b0f1a" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="min-h-full">
        <ThemeProvider>
          <ToastProvider>
            <SkipLink href="#main-content">Skip to main content</SkipLink>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
