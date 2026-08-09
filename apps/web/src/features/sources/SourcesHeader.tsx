"use client";

import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { cn } from "@/lib/cn";

type Props = {
  showPaste: boolean;
  onShowPasteChange: (next: boolean) => void;
  busy: boolean;
};

export function SourcesHeader({ showPaste, onShowPasteChange, busy }: Props) {
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardDescription className="max-w-2xl leading-relaxed">
          Upload a PDF/text file, or paste notes directly. Currently we support PDFs and plain text
          or .mds.
        </CardDescription>
        <Button
          size="sm"
          variant={showPaste ? "outline" : "soft"}
          onClick={() => onShowPasteChange(!showPaste)}
          disabled={busy}
          aria-expanded={showPaste}
          aria-controls="paste-notes-card"
        >
          {/* Rotates to an X while the paste form is open — visible toggle state. */}
          <Plus
            className={cn(
              "h-3.5 w-3.5 transition-transform duration-200 ease-out-expo",
              showPaste && "rotate-45"
            )}
            aria-hidden="true"
          />
          <span className="ml-1.5">{showPaste ? "Hide paste notes" : "Add via paste"}</span>
        </Button>
      </div>
    </Card>
  );
}
