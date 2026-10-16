import type { Metadata, Viewport } from "next";
import { Geist, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/ui/toast";
import { SkipLink } from "@/components/layout/SkipLink";

/** Text — Geist, a neutral grotesque with high legibility at small sizes. */
const fontSans = Geist({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

/** Code, identifiers, and tabular figures. */
const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Cartana | Project Specification Copilot",
  description:
    "Verify pull requests against your project's requirements. Coverage scores, trust levels, and requirement-by-requirement risk alerts.",
  applicationName: "Cartana",
};

export const viewport: Viewport = {
  themeColor: "#010102",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${fontSans.variable} ${fontMono.variable}`}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="min-h-full">
        <ToastProvider>
          <SkipLink href="#main-content">Skip to main content</SkipLink>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
