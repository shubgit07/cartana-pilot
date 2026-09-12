export const POLL_INTERVAL_MS = 1500;
export const POLL_BACKOFF_MS = 3000;
export const TOAST_DURATION_MS = 4000;

export const NAVIGATION_TABS = [
  "requirements",
  "repository",
  "compliance",
  "chat",
] as const;
export type NavigationTab = (typeof NAVIGATION_TABS)[number];
