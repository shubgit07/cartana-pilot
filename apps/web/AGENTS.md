# AGENTS.md — apps/web

Conventions for AI agents and humans editing this frontend.

## Architecture

```
src/
  app/            # Next.js App Router — thin page shells only
  components/
    ui/           # Design-system primitives (Button, Card, Dialog, Select, Tabs, Toast)
    layout/       # AppShell, SkipLink, ThemeToggle, CartanaLogo
    common/       # Cross-feature components (ConfirmDialog, EmptyState, SubmitButton, SourceFileInput)
  features/       # Vertical slices — one folder per domain
    projects/     # Project list + new-project form
    project-detail/ # Project detail page (header, tabs, overview, delete)
    sources/      # Source upload + paste + list + status
    requirements/ # Requirement list + inline edit + accept/reject
    tasks/        # Task list + create + inline edit + accept/reject + requirement select
    chat/         # Chat panel + message list + composer + citations + suggested questions
  hooks/
    api/          # Data hooks (useProjects, useSources, useChat, useRequirements, useTasks, useSourceStatus)
    common/       # Utility hooks (useMediaQuery, useQueryState, useUnsavedChanges)
  lib/
    api/          # API client — one file per resource (projects, sources, chat, requirements, tasks) + client.ts
    theme/        # ThemeProvider, useTheme, inline no-FOUC script
    cn.ts         # tailwind-merge + clsx
    format.ts     # Intl.DateTimeFormat + Intl.NumberFormat helpers
    storage.ts    # SSR-safe typed localStorage
    constants.ts  # Poll intervals, navigation tabs, toast duration
    aria.ts       # Focus ring class, visually-hidden class
```

## Rules

### Structure
- **Each file has one responsibility.** If a component exceeds ~150 lines, split it.
- **Features are vertical slices.** A feature folder contains its panel, rows, forms, badges, empty state, and index barrel. Import from `@/features/<name>`, not internal files.
- **App routes are thin shells.** `page.tsx` renders a feature component and does nothing else.
- **Barrel files (`index.ts`) are the public API.** Consumers import from the barrel, never from internal files.

### UI Primitives
- Use `@/components/ui/*` primitives. Never use raw `<button>`, `<select>`, or `<input>` in feature code — use the wrapped primitives.
- **Never use native `confirm()` or `alert()`.** Use `<ConfirmDialog>` from `@/components/common`.
- **Never use native `<select>`.** Use `<Select>` from `@/components/ui/select` (Radix-based, dark-mode safe).
- **Never use native `<dialog>`.** Use `<Dialog>` from `@/components/ui/dialog` (Radix-based, focus-trapped).

### Accessibility (Vercel Web Interface Guidelines)
- Icon-only buttons need `aria-label`.
- All form controls need `<label>` (via `htmlFor` or wrapping) or `aria-label`.
- Decorative icons need `aria-hidden="true"`.
- Interactive elements need `focus-visible:ring-*` (primitives handle this; custom buttons must add it).
- Use semantic HTML (`<button>`, `<a>`, `<label>`, `<nav>`, `<main>`, `<section>`) before ARIA.
- Headings hierarchical `<h1>`–`<h6>`.
- Skip link to `#main-content` is in `layout.tsx`.
- `aria-live="polite"` on toast viewport (handled in `ToastProvider`).
- `aria-live="polite"` on loading spinners in chat.
- `role="alert"` on error messages.
- `role="status"` on toast viewport.
- `prefers-reduced-motion` respected globally in `globals.css`.
- `text-wrap: balance` on all headings (in `globals.css`).
- `font-variant-numeric: tabular-nums` on numbers (dates, counts, scores) via `.tabular` class.

### Forms
- Inputs need `name`, `autoComplete`, and `spellCheck` attributes.
- `autoComplete="off"` on non-auth fields.
- `spellCheck={false}` on filenames, codes, identifiers.
- Placeholders end with `…` and show example pattern.
- Submit button stays enabled until request starts; spinner during request (use `<SubmitButton>`).
- Errors inline next to fields with `role="alert"`; focus first error on submit.
- Warn before navigation with unsaved changes (`useUnsavedChanges` hook).

### Animation
- Never `transition: all` — list properties explicitly (`transition-colors`, `transition-opacity`).
- `prefers-reduced-motion: reduce` disables all animations (in `globals.css`).
- Animate `transform`/`opacity` only (compositor-friendly).

### Typography
- `…` not `...` for ellipsis.
- Curly quotes `'` `'` `"` `"` in JSX content, not straight quotes.
- Loading states end with `…`: `"Loading…"`, `"Saving…"`, `"Creating…"`.

### Dates & Numbers
- Use `formatDate()` / `formatDateTime()` from `@/lib/format` (backed by `Intl.DateTimeFormat`).
- Never use `new Date().toLocaleDateString()` directly — it causes hydration mismatches.
- Use `formatCount(n, "source")` for count + plural.
- Use `formatScore(n)` for citation scores (2 decimal places).

### Dark Mode
- `ThemeProvider` in `layout.tsx` manages `<html class="dark">` + `color-scheme`.
- Inline `themeScript` runs before hydration to prevent FOUC.
- `ThemeToggle` in `AppShell` header lets users switch.
- CSS variables in `globals.css` (`:root` and `.dark`).
- `tailwind.config.js` uses `darkMode: "class"`.

### State & URL
- Tab state syncs to URL via `useQueryState("tab", ...)` — no `nuqs` dependency.
- Chat history persists to `localStorage` per project (via `useChat` hook).
- `lib/storage.ts` wraps localStorage with SSR safety.

### API & Hooks
- API client is split per resource: `lib/api/{projects,sources,chat,requirements,tasks}.ts`.
- Shared `request<T>()` and `ApiError` in `lib/api/client.ts`.
- Data hooks in `hooks/api/` — one file per resource.
- Hooks return `{ data, loading, error, reload, ...mutations }`.
- `messageOf(e)` helper extracts error messages from unknown catch.

### Linting
- `npx tsc --noEmit` — zero errors.
- `npm run lint -w @cartana/web` — zero errors, zero warnings.
- `npm run build -w @cartana/web` — zero errors, zero warnings.

### Dependencies
- Radix Primitives for accessible components (`react-dialog`, `react-label`, `react-slot`, `react-tabs`, `react-select`).
- `lucide-react` for icons.
- `class-variance-authority` for variant-driven primitives.
- `tailwindcss-animate` for Radix animation utilities.
- No `nuqs`, no `zustand`, no test framework — keep the bundle small.
