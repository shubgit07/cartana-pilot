export const POLL_INTERVAL_MS = 1500;
export const POLL_BACKOFF_MS = 3000;
export const TOAST_DURATION_MS = 4000;

export const NAVIGATION_TABS = ["overview", "sources", "requirements", "tasks", "chat", "audit"] as const;
export type NavigationTab = (typeof NAVIGATION_TABS)[number];
