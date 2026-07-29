"use client";

import * as React from "react";
import { MessageSquare, RefreshCw, Sparkles, Upload } from "lucide-react";
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
  const hasSources = sourceCount > 0;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <StepCard
        step="1"
        icon={<Upload className="h-4 w-4" />}
        title="Upload"
        description="Add briefs, PRDs, or notes."
        body={
          <p className="text-sm leading-relaxed text-muted-foreground">
            {hasSources ? formatSourceSummary(sourceCount) : "No sources yet."}
          </p>
        }
        action={
          <Button
            size="sm"
            onClick={onUploadClick}
            variant={hasSources ? "outline" : "default"}
          >
            <Upload className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="ml-1.5">{hasSources ? "Manage sources" : "Upload now"}</span>
          </Button>
        }
      />

      <StepCard
        step="2"
        icon={<Sparkles className="h-4 w-4" />}
        title="Wait for processing"
        description="Documents are chunked and embedded."
        body={
          <p className="flex flex-wrap items-center gap-1.5 text-sm leading-relaxed text-muted-foreground">
            Sources will show <Badge variant="success">Ready</Badge> once embedded.
          </p>
        }
        action={
          <Button size="sm" variant="outline" onClick={reload}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="ml-1.5">Refresh</span>
          </Button>
        }
      />

      <StepCard
        step="3"
        icon={<MessageSquare className="h-4 w-4" />}
        title="Ask questions"
        description="Grounded chat with citations."
        body={
          <p className="text-sm leading-relaxed text-muted-foreground">
            Get answers tied back to the source documents.
          </p>
        }
        action={
          <Button size="sm" onClick={onChatClick}>
            <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="ml-1.5">Open chat</span>
          </Button>
        }
      />
    </div>
  );
}

function StepCard({
  step,
  icon,
  title,
  description,
  body,
  action,
}: {
  step: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  body: React.ReactNode;
  action: React.ReactNode;
}) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="gap-1.5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
          >
            {icon}
          </span>
          <span className="eyebrow">Step {step}</span>
        </div>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col">
        {body}
        {/* mt-auto keeps the actions aligned across cards of differing body length. */}
        <div className="mt-auto pt-4">{action}</div>
      </CardContent>
    </Card>
  );
}

function formatSourceSummary(n: number) {
  return n === 1 ? "1 source uploaded." : `${n} sources uploaded.`;
}

export function OverviewTabSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-3" aria-busy="true" aria-label="Loading overview">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i} className="flex h-full flex-col">
          <CardHeader className="gap-2.5">
            <div className="flex items-center gap-2">
              <Skeleton className="size-7 rounded-md" />
              <Skeleton className="h-3 w-14" />
            </div>
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <Skeleton className="h-3 w-full" />
            <div className="mt-auto pt-4">
              <Skeleton className="h-8 w-28 rounded-md" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
