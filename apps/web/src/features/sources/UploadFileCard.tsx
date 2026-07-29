"use client";

import { Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { SourceFileInput } from "@/components/common/SourceFileInput";
import { useToast } from "@/components/ui/toast";
import { useSources } from "@/hooks/api";
import { messageOf } from "@/hooks/api";

type Props = {
  projectId: string;
  busy: boolean;
  onBusyChange: (next: boolean) => void;
};

export function UploadFileCard({ projectId, busy, onBusyChange }: Props) {
  const { uploadFile } = useSources(projectId);
  const { toast } = useToast();

  async function handle(file: File) {
    onBusyChange(true);
    try {
      await uploadFile(file);
      toast({ title: "Upload started", description: `${file.name} is processing…` });
    } catch (e: unknown) {
      toast({
        title: "Upload failed",
        description: messageOf(e) ?? "Try again",
        variant: "destructive",
      });
    } finally {
      onBusyChange(false);
    }
  }

  return (
    <Card>
      <CardHeader className="gap-1.5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="inline-flex size-7 items-center justify-center rounded-md border border-primary/20 bg-primary-soft text-primary-soft-foreground"
          >
            <Upload className="h-4 w-4" />
          </span>
          <span className="eyebrow">Upload</span>
        </div>
        <CardTitle className="text-base">Upload a file</CardTitle>
        <CardDescription className="leading-relaxed">
          PDF or plain text (≤ a few MB). Larger files upload in chunks.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <SourceFileInput onFile={handle} disabled={busy} loading={busy} />
        <p className="mt-3 text-2xs leading-relaxed text-muted-foreground">
          Files are chunked and embedded automatically — no extra step needed.
        </p>
      </CardContent>
    </Card>
  );
}
