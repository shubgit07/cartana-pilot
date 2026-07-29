import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ProjectGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      aria-busy="true"
      aria-live="polite"
      aria-label="Loading projects"
    >
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="flex h-full flex-col">
          <CardHeader className="gap-2.5">
            <div className="flex items-start justify-between gap-3">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-4 w-4 shrink-0 rounded-sm" />
            </div>
            <div className="space-y-1.5">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
            </div>
          </CardHeader>
          <CardContent className="mt-auto flex items-center justify-between gap-3 border-t border-border/70 pt-4">
            <Skeleton className="h-5 w-20 rounded-md" />
            <Skeleton className="h-3 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
