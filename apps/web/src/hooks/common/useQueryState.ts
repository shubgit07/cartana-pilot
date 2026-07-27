"use client";

import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type QueryState<T extends string> = [T, (next: T) => void];

const isInferred = <T extends string>(value: string | null, allowed: readonly T[]): value is T =>
  value !== null && (allowed as readonly string[]).includes(value);

export function useQueryState<T extends string>(
  key: string,
  allowed: readonly T[],
  fallback: T
): QueryState<T> {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const current = React.useMemo(() => {
    const raw = params?.get(key) ?? null;
    return isInferred(raw, allowed) ? raw : fallback;
  }, [params, allowed, fallback, key]);

  const set = React.useCallback(
    (next: T) => {
      const sp = new URLSearchParams(params?.toString() ?? "");
      if (next === fallback) sp.delete(key);
      else sp.set(key, next);
      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [fallback, params, pathname, router, key]
  );

  return [current, set];
}
