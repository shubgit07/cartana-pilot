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
import { Label } from "@/components/ui/label";
import { SubmitButton } from "@/components/common/SubmitButton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  Code2,
  FileCode2,
  FolderGit2,
  GitBranch,
  GitCommit,
  Github,
  Layers,
  Loader2,
  RefreshCw,
  Search,
  Unplug,
} from "lucide-react";
import { useToast } from "@/components/ui/toast";
import { useRepository } from "@/hooks/api/repository";
import { messageOf } from "@/hooks/api";
import { formatCount } from "@/lib/format";

type Props = {
  projectId: string;
};

export function RepositoryPanel({ projectId }: Props) {
  const { toast } = useToast();
  const {
    status,
    loading,
    syncing,
    error,
    connectRepo,
    resync,
    disconnectRepo,
  } = useRepository(projectId);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [repoUrl, setRepoUrl] = React.useState("");
  const [confirmDisconnect, setConfirmDisconnect] = React.useState(false);

  const files = React.useMemo(() => status?.files ?? [], [status]);
  const filteredFiles = files.filter((f) =>
    f.path.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const connected = status?.connected === true;

  React.useEffect(() => {
    setRepoUrl("");
    setSearchQuery("");
    setConfirmDisconnect(false);
  }, [projectId]);

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    const url = repoUrl.trim();
    if (!url) return;
    try {
      const result = await connectRepo(url);
      setRepoUrl("");
      toast({
        title: "Repository connected",
        description: `${result.displayName}: ${formatCount(result.filesIndexed, "file")} synced into ${formatCount(result.chunksCreated, "chunk")}.`,
      });
    } catch (err: unknown) {
      toast({
        title: "Connection failed",
        description: messageOf(err) ?? "Use a public github.com URL like https://github.com/owner/repo",
        variant: "destructive",
      });
    }
  }

  async function handleResync() {
    try {
      const result = await resync();
      toast(
        result.upToDate
          ? { title: "Already up to date", description: `Codebase Index matches ${result.commitSha.slice(0, 7)}.` }
          : {
              title: "Codebase Index synced",
              description: `${formatCount(result.filesIndexed, "file")} synced into ${formatCount(result.chunksCreated, "chunk")}.`,
            }
      );
    } catch (err: unknown) {
      toast({
        title: "Sync failed",
        description: messageOf(err) ?? "Try again",
        variant: "destructive",
      });
    }
  }

  async function handleDisconnect() {
    try {
      await disconnectRepo();
      setConfirmDisconnect(false);
      toast({ title: "Repository disconnected", description: "Codebase Index cleared." });
    } catch (err: unknown) {
      toast({
        title: "Disconnect failed",
        description: messageOf(err) ?? "Try again",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Connect / Connected Card */}
      <Card className="border-border/80 bg-surface">
        <CardHeader className="gap-3 border-b border-border/70 pb-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Version Control</span>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FolderGit2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Codebase Index
              </CardTitle>
              <CardDescription>
                Link a public GitHub repository. We sync its code (never assets or
                dependencies) into a searchable index for requirement verification.
              </CardDescription>
            </div>

            {connected && (
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => void handleResync()} disabled={syncing}>
                  <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} aria-hidden="true" />
                  <span className="ml-1.5">{syncing ? "Syncing…" : "Sync latest"}</span>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setConfirmDisconnect(true)}
                  disabled={syncing}
                  className="hover:border-danger/40 hover:bg-danger-soft hover:text-danger-soft-foreground"
                >
                  <Unplug className="h-3.5 w-3.5" aria-hidden="true" />
                  <span className="ml-1.5">Disconnect</span>
                </Button>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="pt-5">
          {loading && (
            <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground" aria-live="polite">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              Loading…
            </div>
          )}

          {!loading && error && !connected && (
            <p role="alert" className="max-w-xl py-2 text-xs text-danger-soft-foreground">
              {error}
            </p>
          )}

          {!loading && !connected && (
            <form onSubmit={handleConnect} className="max-w-xl space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="github-repo-url">Public GitHub repository URL</Label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <div className="relative flex-1">
                    <Github className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                    <Input
                      id="github-repo-url"
                      name="githubRepoUrl"
                      autoComplete="off"
                      spellCheck={false}
                      placeholder="https://github.com/owner/repo…"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      className="pl-8 font-mono text-xs"
                      disabled={syncing}
                    />
                  </div>
                  <SubmitButton type="submit" loading={syncing} loadingLabel="Connecting…" disabled={!repoUrl.trim()}>
                    Connect & sync
                  </SubmitButton>
                </div>
                <p className="text-2xs leading-relaxed text-muted-foreground">
                  Public repositories only during the free MVP. Private repos arrive later.
                </p>
              </div>
            </form>
          )}

          {!loading && connected && status && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Linked Repository
                </span>
                <div className="mt-1 flex items-center gap-1.5 font-mono text-xs font-medium text-foreground">
                  <Github className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="truncate" title={status.repoUrl ?? undefined}>
                    {status.repoUrl?.replace("https://github.com/", "") ?? "—"}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-2xs text-muted-foreground">
                  <GitBranch className="h-3 w-3" aria-hidden="true" />
                  <span className="truncate">{status.refName ?? "—"}</span>
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Index Synced At
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
                  Synced Files
                </span>
                <div className="mt-1 text-xs font-medium text-foreground tabular">
                  {formatCount(status.indexedFilesCount, "file")}
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-surface-sunken p-3">
                <span className="text-2xs font-medium text-muted-foreground uppercase tracking-wider">
                  Code Chunks
                </span>
                <div className="mt-1 flex items-center gap-1.5 text-xs font-medium text-foreground">
                  <Layers className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span className="tabular">{formatCount(status.codeChunksCount, "chunk")}</span>
                  <span className="text-2xs text-muted-foreground">({status.embeddingDim}-dim)</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Synced Files Section */}
      <Card>
        <CardHeader className="gap-3 border-b border-border/70">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <span className="eyebrow">Codebase Index</span>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileCode2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                Synced Files ({files.length})
              </CardTitle>
              <CardDescription>
                Repository code chunked and embedded for requirement verification.
              </CardDescription>
            </div>

            <div className="relative w-full max-w-xs">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              <Input
                placeholder="Search synced files…"
                aria-label="Search synced files"
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
                {connected
                  ? "No matching synced files found."
                  : "Connect a GitHub repository above to build the Codebase Index."}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmDisconnect}
        onOpenChange={setConfirmDisconnect}
        title="Disconnect repository?"
        description="This clears the Codebase Index (synced files and code vectors). Your documents and requirements stay."
        confirmLabel="Disconnect"
        cancelLabel="Keep connected"
        destructive
        loading={syncing}
        onConfirm={() => void handleDisconnect()}
      />
    </div>
  );
}
