"use client";

import * as React from "react";

/**
 * Warns the user before navigating away (including full reloads) when
 * `dirty` is true. Uses the modern `beforeunload` event for browser
 * reloads/closures.
 */
export function useUnsavedChanges(dirty: boolean): void {
  React.useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
}
