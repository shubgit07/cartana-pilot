"use client";

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
      <CardHeader>
        <CardTitle>Upload a file</CardTitle>
        <CardDescription>PDF or plain text (≤ a few MB). Larger files upload in chunks.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-3">
        <SourceFileInput onFile={handle} disabled={busy} loading={busy} />
      </CardContent>
    </Card>
  );
}
