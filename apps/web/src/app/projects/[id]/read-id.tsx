"use client";

import { useParams } from "next/navigation";

export function ReadId({ children }: { children: (id: string) => React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  return <>{children(id)}</>;
}
