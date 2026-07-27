"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type Props = {
  sourceCount: number;
  onUploadClick: () => void;
  onChatClick: () => void;
  reload: () => void;
};

export function OverviewTab({ sourceCount, onUploadClick, onChatClick, reload }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <StepCard
        step="1"
        title="Upload"
        description="Add briefs, PRDs, or notes."
        body={
          <>
            <p className="text-sm text-muted-foreground">
              {sourceCount === 0
                ? "No sources yet."
                : formatSourceSummary(sourceCount)}
            </p>
            <Button
              size="sm"
              className="mt-3"
              onClick={onUploadClick}
              variant={sourceCount === 0 ? "default" : "outline"}
            >
              {sourceCount === 0 ? "Upload now" : "Manage sources"}
            </Button>
          </>
        }
      />
      <StepCard
        step="2"
        title="Wait for processing"
        description="Documents are chunked and embedded."
        body={
          <>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              Sources will show <Badge variant="success">Ready</Badge> once embedded.
            </p>
            <Button size="sm" variant="outline" className="mt-3" onClick={reload}>
              Refresh
            </Button>
          </>
        }
      />
      <StepCard
        step="3"
        title="Ask questions"
        description="Grounded chat with citations."
        body={
          <>
            <p className="text-sm text-muted-foreground">
              Get answers tied back to the source documents.
            </p>
            <Button size="sm" className="mt-3" onClick={onChatClick}>
              Open chat
            </Button>
          </>
        }
      />
    </div>
  );
}

function StepCard({
  step,
  title,
  description,
  body,
}: {
  step: string;
  title: string;
  description: string;
  body: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground tabular">
            {step}
          </span>
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}

function formatSourceSummary(n: number) {
  return n === 1 ? "1 source uploaded." : `${n} sources uploaded.`;
}

export function OverviewTabSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardHeader className="space-y-2">
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-8 w-1/3" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
