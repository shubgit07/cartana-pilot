import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/ui/toast";
import { ThemeProvider, themeScript } from "@/lib/theme";
import { SkipLink } from "@/components/layout/SkipLink";

/** UI / body — neutral grotesque, high legibility at small sizes. */
const fontSans = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

/** Display — modern geometric sans-serif for hero and headings. */
const fontSerif = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
});


/** Code, identifiers, and tabular figures. */
const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Cartana — Project Specification Copilot",
  description: "Turn project documents into a clear execution plan.",
  applicationName: "Cartana",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf9f7" },
    { media: "(prefers-color-scheme: dark)", color: "#191919" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${fontSans.variable} ${fontSerif.variable} ${fontMono.variable}`}
    >
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
