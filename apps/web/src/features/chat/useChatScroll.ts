"use client";

import * as React from "react";

export function useChatScroll(deps: React.DependencyList) {
  const ref = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: reduce ? "auto" : "smooth",
    });
    // react-hooks lint allows deps through the function signature.
  }, deps);

  return ref;
}
