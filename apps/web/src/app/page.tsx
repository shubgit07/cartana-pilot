import * as React from "react";
import { ProjectList } from "@/features/projects";

export default function HomePage() {
  return (
    <React.Suspense
      fallback={
        <div className="space-y-1.5" aria-busy="true" aria-label="Loading projects">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-11 animate-pulse rounded-lg bg-surface-hover/60" />
          ))}
        </div>
      }
    >
      <ProjectList />
    </React.Suspense>
  );
}
