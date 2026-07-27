import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/EmptyState";

export function SourcesEmptyHint() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Add project material</CardTitle>
        <CardDescription>
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

export function SourcesEmptyList() {
  return (
    <EmptyState
      icon="inbox"
      title="No sources yet"
      description="Once you upload a document, it will appear here. Refresh after the chunk + embedding pipeline finishes."
    />
  );
}
