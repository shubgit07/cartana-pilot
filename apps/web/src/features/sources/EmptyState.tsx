import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/EmptyState";

/** First-run hint shown when a project has no sources at all. */
export function SourcesEmptyHint() {
  return (
    <Card>
      <CardHeader className="gap-1.5">
        <span className="eyebrow">Material</span>
        <CardTitle className="font-serif text-xl leading-tight">Add project material</CardTitle>
        <CardDescription className="max-w-2xl leading-relaxed">
          Upload a PDF or text file, or paste notes directly. Phase 1 supports PDF and plain text.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon="inbox"
          title="No sources yet"
          description="Upload a brief or paste notes to get started."
        />
      </CardContent>
    </Card>
  );
}

/** Shown in place of the source list while it is empty. */
export function SourcesEmptyList() {
  return (
    <EmptyState
      icon="inbox"
      title="No sources yet"
      description="Once you upload a document, it appears here while the chunking and embedding pipeline runs."
    />
  );
}
