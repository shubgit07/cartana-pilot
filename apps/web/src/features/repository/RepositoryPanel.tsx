"use client";

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Code2,
  FileCode2,
  FileUp,
  FolderGit2,
  GitCommit,
  Layers,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { useRepository } from "@/hooks/api/repository";
import { formatCount } from "@/lib/format";

type Props = {
  projectId: string;
};

export function RepositoryPanel({ projectId }: Props) {
  const { toast } = useToast();
  const { status, loading, syncing, error, reload, syncFiles } = useRepository(projectId);
  const [searchQuery, setSearchQuery] = React.useState("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const files = React.useMemo(
    () => status?.files ?? [],
    [status]
  );
  const filteredFiles = files.filter((f) =>
    f.path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  async function handlePickedFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files;
    e.target.value = "";
    if (!picked || picked.length === 0) return;
    try {
      const result = await syncFiles(picked);
      if (result) {
        toast({
          title: "Repository Index Synced",
          description: `${formatCount(result.filesIndexed, "file")} indexed into ${formatCount(result.chunksCreated, "chunk")}.`,
        });
      }
    } catch {
      toast({
        title: "Sync Failed",
        description: "Could not index the selected files.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Repository Index Card */}
      <Card className="border-border/80 bg-surface">
        <CardHeader className="gap-3 border-b border-border/70 pb-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Version Control</span>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FolderGit2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Repository Code Index
              </CardTitle>
              <CardDescription>
                Workspace snapshot chunked and embedded for requirement verification.
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                aria-label="Select source files to index"
                onChange={(e) => void handlePickedFiles(e)}
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={syncing}
              >
                <FileUp className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="ml-1.5">{syncing ? "Indexing…" : "Select Files & Index"}</span>
              </Button>
              <Button size="sm" variant="outline" onClick={() => void reload()} disabled={loading}>
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
                <span className="ml-1.5">Refresh</span>
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-5">
          {loading && (
            <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground" aria-live="polite">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              Loading…
            </div>
          )}

          {!loading && error && (
            <div className="max-w-xl space-y-2 py-2 text-xs" role="alert">
              <p className="text-foreground">{error}</p>
              <Button size="sm" variant="outline" onClick={() => void reload()}>
                Retry
              </Button>
            </div>
          )}

          {!loading && !error && (!status || !status.connected) && (
            <div className="max-w-xl space-y-2 py-2 text-xs text-muted-foreground">
              <p>No code index yet. Select source files to build the first snapshot.</p>
            </div>
          )}

          {!loading && !error && status?.connected && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Active Commit Snapshot
                </span>
                <div className="mt-1 flex items-center gap-1.5 font-mono text-xs font-medium text-foreground">
                  <GitCommit className="h-3.5 w-3.5 text-success" aria-hidden="true" />
                  <span className="truncate">{status.commitSha?.slice(0, 10) ?? "—"}</span>
                  <Badge variant="success" className="text-2xs py-0 px-1">
                    {status.status}
                  </Badge>
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Indexed Files
                </span>
                <div className="mt-1 text-xs font-medium text-foreground tabular">
                  {formatCount(status.indexedFilesCount, "file")}
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Indexed Chunks
                </span>
                <div className="mt-1 flex items-center gap-1.5 text-xs font-medium text-foreground">
                  <Layers className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span className="tabular">{formatCount(status.codeChunksCount, "chunk")}</span>
                  <span className="text-2xs text-muted-foreground">({status.embeddingDim}-dim)</span>
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Reference
                </span>
                <div className="mt-1 font-mono text-xs font-medium text-foreground truncate">
                  {status.refName ?? "workspace snapshot"}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Code Chunk & File Index Section */}
      <Card>
        <CardHeader className="gap-3 border-b border-border/70">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Semantic Code Index</span>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileCode2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Indexed Repository Files ({files.length})
              </CardTitle>
              <CardDescription>
                Source files chunked and embedded with vector representations for requirement verification.
              </CardDescription>
            </div>

            <div className="relative w-full max-w-xs">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              <Input
                placeholder="Search indexed files…"
                aria-label="Search indexed files"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs font-mono"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-4">
          <div className="divide-y divide-border/60">
            {filteredFiles.map((file) => (
              <div
                key={file.path}
                className="flex items-center justify-between py-2.5 px-2 hover:bg-surface-hover/50 rounded-md transition-colors text-xs"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <Code2 className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
                  <span className="font-mono text-foreground truncate font-medium">
                    {file.path}
                  </span>
                  {file.language && (
                    <Badge variant="outline" className="text-2xs py-0 px-1 font-mono">
                      {file.language}
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-4 text-2xs text-muted-foreground shrink-0 tabular">
                  <span>{file.lineCount ?? "—"} lines</span>
                  <span>{(file.sizeBytes / 1024).toFixed(1)} KB</span>
                  <span className="rounded bg-surface-sunken px-1.5 py-0.5 border border-border/50 text-foreground font-mono">
                    {file.chunksCount} chunks
                  </span>
                </div>
              </div>
            ))}

            {filteredFiles.length === 0 && (
              <div className="py-6 text-center text-xs text-muted-foreground">
                No matching indexed files found.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
