import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
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

/** Display — geometric sans (Poppins) for hero and headings. */
const fontSerif = localFont({
  src: [
    { path: "./fonts/Poppins-SemiBold.ttf", weight: "600" },
    { path: "./fonts/Poppins-Black.ttf", weight: "900" },
  ],
  variable: "--font-serif",
  display: "swap",
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
