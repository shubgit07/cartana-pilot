"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

type Props = {
  action: "upload" | "paste" | "both";
  showPaste: boolean;
  onShowPasteChange: (next: boolean) => void;
  busy: boolean;
};

export function SourcesHeader({ action, showPaste, onShowPasteChange, busy }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Add project material</CardTitle>
        <CardDescription>
          {action === "upload" && "Upload a PDF or text file. Phase 1 supports PDF and plain text."}
          {action === "paste" && "Paste in notes directly. They’re stored as a text source for the same pipeline."}
          {action === "both" && "Upload a PDF/text file, or paste notes directly. Phase 1 supports PDF and plain text."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant={showPaste ? "outline" : "default"}
          onClick={() => onShowPasteChange(!showPaste)}
          disabled={busy}
          aria-expanded={showPaste}
          aria-controls="paste-notes-card"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          <span className="ml-1.5">{showPaste ? "Hide paste notes" : "Add via paste"}</span>
        </Button>
      </CardContent>
    </Card>
  );
}
