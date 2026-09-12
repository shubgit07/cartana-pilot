import * as React from "react";
import {
  AlertTriangle,
  Bug,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code2,
  Copy,
  Download,
  ExternalLink,
  FileCode2,
  FileDiff,
  FileJson,
  GitPullRequest,
  Info,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import { useVerifyPR } from "@/hooks/api/audit";
import { downloadFile, formatPRBriefAsGithubMarkdown } from "@/lib/formatPrBrief";
import type {
  PRRiskAlert,
  PRTrustBrief,
  RequirementVerificationVerdict,
  VerificationVerdictStatus,
} from "@cartana/shared";

type Props = {
  projectId: string;
  externalBrief?: import("@cartana/shared").PRTrustBrief | null;
};

const VERDICT_STYLES: Record<
  VerificationVerdictStatus,
  { badge: string; icon: React.ComponentType<{ className?: string }>; label: string }
> = {
  covered: {
    badge: "border-success/30 bg-success-soft text-success-soft-foreground",
    icon: CheckCircle2,
    label: "Covered",
  },
  partial: {
    badge: "border-warning/30 bg-warning-soft text-warning-soft-foreground",
    icon: AlertTriangle,
    label: "Partial",
  },
  missing: {
    badge: "border-danger/30 bg-danger-soft text-danger-soft-foreground",
    icon: Bug,
    label: "Missing",
  },
  unclear: {
    badge: "border-border bg-muted text-muted-foreground",
    icon: Info,
    label: "Unclear",
  },
};

const TRUST_STYLES = {
  high: {
    border: "border-success/40",
    bg: "bg-success-soft/40",
    text: "text-success-soft-foreground",
    badge: "bg-success text-success-foreground",
    glow: "shadow-[0_0_24px_-4px_rgba(34,197,94,0.3)]",
  },
  medium: {
    border: "border-warning/40",
    bg: "bg-warning-soft/40",
    text: "text-warning-soft-foreground",
    badge: "bg-warning text-warning-foreground",
    glow: "shadow-[0_0_24px_-4px_rgba(245,158,11,0.3)]",
  },
  low: {
    border: "border-danger/40",
    bg: "bg-danger-soft/40",
    text: "text-danger-soft-foreground",
    badge: "bg-danger text-danger-foreground",
    glow: "shadow-[0_0_24px_-4px_rgba(239,68,68,0.3)]",
  },
};

export function PRTrustBriefDashboard({ projectId, externalBrief = null }: Props) {
  const { brief, fromCache, verifying, error, verify, loadBrief } = useVerifyPR(projectId);
  const { toast } = useToast();

  React.useEffect(() => {
    if (externalBrief) loadBrief(externalBrief);
  }, [externalBrief, loadBrief]);

  const [copied, setCopied] = React.useState(false);
  const [inputTab, setInputTab] = React.useState<"paste_diff" | "github_pr">("paste_diff");
  const [rawDiff, setRawDiff] = React.useState("");
  const [githubPrUrl, setGithubPrUrl] = React.useState("");
  const [specText, setSpecText] = React.useState("");
  const [showSpecInput, setShowSpecInput] = React.useState(false);
  const [expandedReqs, setExpandedReqs] = React.useState<Record<string, boolean>>({});
  const [userOverrides, setUserOverrides] = React.useState<
    Record<string, { status: VerificationVerdictStatus; rationale?: string }>
  >({});

  const toggleReq = (reqId: string) => {
    setExpandedReqs((prev) => ({ ...prev, [reqId]: !prev[reqId] }));
  };

  const handleOverrideStatus = (reqId: string, newStatus: string) => {
    if (newStatus === "__RESET__") {
      setUserOverrides((prev) => {
        const next = { ...prev };
        delete next[reqId];
        return next;
      });
      toast({ title: "Reset to AI Verdict", description: `Requirement ${reqId} restored to AI judgment.` });
      return;
    }

    const validStatus = newStatus as VerificationVerdictStatus;
    setUserOverrides((prev) => ({
      ...prev,
      [reqId]: { status: validStatus, rationale: "Developer ground-truth override" },
    }));
    toast({
      title: "Human-in-the-Loop Override Applied",
      description: `Requirement ${reqId} marked as ${validStatus.toUpperCase()} by developer.`,
    });
  };

  const handleCopyGithubComment = async () => {
    if (!brief) return;
    const md = formatPRBriefAsGithubMarkdown(brief);
    try {
      await navigator.clipboard.writeText(md);
      setCopied(true);
      toast({
        title: "Copied to clipboard!",
        description: "Formatted GitHub comment is ready to paste into PR review box.",
      });
      setTimeout(() => setCopied(false), 3000);
    } catch {
      toast({
        title: "Copy failed",
        description: "Could not copy to clipboard.",
        variant: "destructive",
      });
    }
  };

  const handleDownloadMarkdown = () => {
    if (!brief) return;
    const md = formatPRBriefAsGithubMarkdown(brief);
    downloadFile(`PR_TRUST_BRIEF_${brief.projectId}.md`, md, "text/markdown;charset=utf-8");
    toast({ title: "Downloaded PR_TRUST_BRIEF.md" });
  };

  const handleDownloadJSON = () => {
    if (!brief) return;
    const jsonStr = JSON.stringify(brief, null, 2);
    downloadFile(`PR_TRUST_BRIEF_${brief.projectId}.json`, jsonStr, "application/json;charset=utf-8");
    toast({ title: "Downloaded PR_TRUST_BRIEF.json" });
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputTab === "paste_diff" && !rawDiff.trim()) {
      toast({
        title: "Diff required",
        description: "Please paste a git diff to verify.",
        variant: "destructive",
      });
      return;
    }
    if (inputTab === "github_pr" && !githubPrUrl.trim()) {
      toast({
        title: "GitHub URL required",
        description: "Please provide a valid GitHub Pull Request URL.",
        variant: "destructive",
      });
      return;
    }

    try {
      await verify({
        rawDiff: inputTab === "paste_diff" ? rawDiff : undefined,
        githubPrUrl: inputTab === "github_pr" ? githubPrUrl : undefined,
        specText: specText.trim() ? specText : undefined,
      });
      toast({
        title: "Audit complete",
        description: "PR Trust Brief successfully generated.",
      });
    } catch (err: unknown) {
      toast({
        title: "Verification failed",
        description: error || "Failed to analyze PR diff.",
        variant: "destructive",
      });
    }
  };

  // ---- Human-in-the-Loop Effective Metrics Calculation ----
  const effectiveVerdicts = React.useMemo(() => {
    if (!brief) return [];
    return brief.verdicts.map((v) => {
      const override = userOverrides[v.reqId];
      if (override) {
        return {
          ...v,
          status: override.status,
          rationale: `${v.rationale} (User Ground-Truth: ${override.rationale})`,
          isUserOverridden: true,
        };
      }
      return { ...v, isUserOverridden: false };
    });
  }, [brief, userOverrides]);

  const effectiveCovered = effectiveVerdicts.filter((v) => v.status === "covered").length;
  const effectivePartial = effectiveVerdicts.filter((v) => v.status === "partial").length;
  const effectiveMissing = effectiveVerdicts.filter((v) => v.status === "missing").length;

  const totalReqs = brief ? brief.totalRequirements : 0;
  const effectiveScore = totalReqs > 0
    ? Math.round(((effectiveCovered + 0.5 * effectivePartial) / totalReqs) * 100)
    : 0;

  const effectiveTrustLevel: "high" | "medium" | "low" =
    effectiveScore >= 80 ? "high" : effectiveScore >= 50 ? "medium" : "low";

  return (
    <div className="space-y-8">
      {/* PR Input Drawer / Form Card */}
      <Card className="border-border/80 bg-card/60 backdrop-blur-sm shadow-soft">
        <CardHeader className="pb-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-soft text-primary">
                  <GitPullRequest className="h-4 w-4" />
                </span>
                <CardTitle className="text-base font-semibold">PR Verification & Trust Audit</CardTitle>
              </div>
              <CardDescription>
                Verify code changes strictly against requirements, pinpoint missing backend logic, and calculate PR Trust.
              </CardDescription>
            </div>

            <div className="flex items-center rounded-lg border border-border/70 bg-muted/40 p-1">
              <button
                type="button"
                onClick={() => setInputTab("paste_diff")}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                  inputTab === "paste_diff"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <FileDiff className="h-3.5 w-3.5" />
                Paste Diff
              </button>
              <button
                type="button"
                onClick={() => setInputTab("github_pr")}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                  inputTab === "github_pr"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <ExternalLink className="h-3.5 w-3.5" />
                GitHub PR URL
              </button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleVerify} className="space-y-4">
            {inputTab === "paste_diff" ? (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Git Diff</label>
                <Textarea
                  value={rawDiff}
                  onChange={(e) => setRawDiff(e.target.value)}
                  placeholder="Paste `git diff` output or PR patch here (e.g. diff --git a/src/auth.ts b/src/auth.ts...)"
                  className="font-mono text-xs h-32 leading-relaxed resize-y"
                  disabled={verifying}
                />
              </div>
            ) : (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">GitHub Pull Request URL</label>
                <Input
                  value={githubPrUrl}
                  onChange={(e) => setGithubPrUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo/pull/123"
                  className="text-sm font-mono"
                  disabled={verifying}
                />
              </div>
            )}

            <div>
              <button
                type="button"
                onClick={() => setShowSpecInput(!showSpecInput)}
                className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
              >
                {showSpecInput ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                {showSpecInput ? "Hide custom spec input" : "Add custom spec markdown (optional)"}
              </button>

              {showSpecInput && (
                <div className="mt-2 space-y-1.5">
                  <Textarea
                    value={specText}
                    onChange={(e) => setSpecText(e.target.value)}
                    placeholder="Optional: Paste ad-hoc feature requirements / PRD text. If blank, Cartana uses this project's active requirements."
                    className="text-xs h-24"
                    disabled={verifying}
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button type="submit" disabled={verifying} className="gap-2">
                {verifying ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing Code & Gaps…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Run Trust Brief Audit
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Audit Results Dashboard */}
      {brief && (
        <div className="space-y-8 animate-fade-in">
          {/* Executive Hero Trust Card */}
          <div
            className={cn(
              "rounded-xl border p-6 transition-all",
              TRUST_STYLES[effectiveTrustLevel].border,
              TRUST_STYLES[effectiveTrustLevel].bg,
              TRUST_STYLES[effectiveTrustLevel].glow
            )}
          >
            <div className="flex flex-wrap items-start justify-between gap-6">
              <div className="space-y-3 max-w-2xl">
                <div className="flex flex-wrap items-center gap-2.5">
                  <Badge className={cn("px-3 py-1 text-xs font-bold uppercase tracking-wider", TRUST_STYLES[effectiveTrustLevel].badge)}>
                    <ShieldCheck className="mr-1.5 h-3.5 w-3.5 inline" />
                    {effectiveTrustLevel} Trust
                  </Badge>

                  {Object.keys(userOverrides).length > 0 && (
                    <Badge variant="outline" className="border-primary/40 bg-background/80 text-primary text-xs gap-1 font-mono">
                      <UserCheck className="h-3 w-3 text-primary" />
                      {Object.keys(userOverrides).length} Human Override(s)
                    </Badge>
                  )}

                  {fromCache && (
                    <Badge variant="outline" className="border-primary/40 bg-background/80 text-primary text-xs gap-1 font-mono">
                      <Zap className="h-3 w-3 text-amber-500 fill-amber-500" />
                      ⚡ 0ms Cached Run (0 Tokens)
                    </Badge>
                  )}
                </div>

                <p className="text-sm font-medium leading-relaxed text-foreground">{brief.summary}</p>
              </div>

              {/* Big Score Radial/Metric */}
              <div className="flex flex-col items-center justify-center rounded-xl border border-border/80 bg-background/90 px-6 py-4 shadow-sm text-center">
                <span className="text-3xl font-black tracking-tight font-serif text-foreground">
                  {effectiveScore}%
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Code Coverage
                </span>
              </div>
            </div>

            {/* Quick Metrics Bar & Export Actions */}
            <div className="mt-6 space-y-4 pt-6 border-t border-border/40">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg bg-background/60 p-3 border border-border/40">
                  <span className="text-xs text-muted-foreground">Total Requirements</span>
                  <p className="text-lg font-bold tabular-nums text-foreground">{totalReqs}</p>
                </div>
                <div className="rounded-lg bg-background/60 p-3 border border-border/40">
                  <span className="text-xs text-success">Covered in Diff</span>
                  <p className="text-lg font-bold tabular-nums text-success">{effectiveCovered}</p>
                </div>
                <div className="rounded-lg bg-background/60 p-3 border border-border/40">
                  <span className="text-xs text-warning">Partially Covered</span>
                  <p className="text-lg font-bold tabular-nums text-warning">{effectivePartial}</p>
                </div>
                <div className="rounded-lg bg-background/60 p-3 border border-border/40">
                  <span className="text-xs text-danger">Missing / Absent</span>
                  <p className="text-lg font-bold tabular-nums text-danger">{effectiveMissing}</p>
                </div>
              </div>

              {/* Action Buttons: Copy as GitHub PR Comment & Download */}
              <div className="flex flex-wrap items-center justify-end gap-2.5 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCopyGithubComment}
                  className="gap-2 bg-background/80 hover:bg-background text-xs font-semibold shadow-xs"
                >
                  {copied ? (
                    <>
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                      Copied GitHub Comment!
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-primary" />
                      Copy as GitHub PR Comment
                    </>
                  )}
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleDownloadMarkdown}
                  className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  <Download className="h-3.5 w-3.5" />
                  Export .md
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleDownloadJSON}
                  className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  <FileJson className="h-3.5 w-3.5" />
                  Export .json
                </Button>
              </div>
            </div>
          </div>

          {/* Risk Alerts Section */}
          {brief.riskAlerts.length > 0 && (
            <Card className="border-danger/30 bg-danger-soft/20">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 text-danger">
                  <ShieldAlert className="h-5 w-5" />
                  <CardTitle className="text-base font-semibold">Security & Architecture Risk Alerts</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {brief.riskAlerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 rounded-lg border border-danger/20 bg-background/80 p-3.5 shadow-2xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={alert.severity === "critical" ? "danger" : "secondary"}
                          className="text-[10px] uppercase font-bold px-2 py-0.5"
                        >
                          {alert.severity}
                        </Badge>
                        <span className="text-sm font-semibold text-foreground">{alert.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{alert.description}</p>
                    </div>

                    {alert.affectedFiles && alert.affectedFiles.length > 0 && (
                      <div className="flex flex-wrap gap-1 shrink-0">
                        {alert.affectedFiles.map((file, fIdx) => (
                          <span
                            key={fIdx}
                            className="rounded bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground border border-border/60"
                          >
                            {file}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Requirement Verification Matrix */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-base font-semibold">Requirement Verification Matrix</CardTitle>
                  <CardDescription>
                    Strict mapping of each requirement to code diff hunks with interactive Human-in-the-Loop developer ground-truth overrides.
                  </CardDescription>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {effectiveVerdicts.length} Requirements
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-0 divide-y divide-border/60">
              {effectiveVerdicts.map((v) => {
                const config = VERDICT_STYLES[v.status] || VERDICT_STYLES.unclear;
                const Icon = config.icon;
                const isExpanded = expandedReqs[v.reqId];

                return (
                  <div key={v.reqId} className="p-4 transition-colors hover:bg-muted/20">
                    <div
                      onClick={() => toggleReq(v.reqId)}
                      className="flex cursor-pointer items-start justify-between gap-4"
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <button type="button" className="mt-0.5 text-muted-foreground">
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </button>

                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-primary">{v.reqId}</span>
                            <span className="text-sm font-medium text-foreground truncate">{v.title}</span>
                            {v.isUserOverridden && (
                              <Badge variant="outline" className="text-[10px] font-bold border-primary/50 text-primary px-1.5 py-0.2">
                                <UserCheck className="mr-1 h-3 w-3 inline" />
                                User Verified
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-2">{v.rationale}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <Badge className={cn("text-xs font-semibold gap-1 px-2.5 py-0.5", config.badge)}>
                          <Icon className="h-3.5 w-3.5" />
                          {config.label}
                        </Badge>
                      </div>
                    </div>

                    {/* Collapsible Evidence Snippet Drawer + Developer Override Controls */}
                    {isExpanded && (
                      <div className="mt-4 ml-7 rounded-lg border border-border/70 bg-muted/40 p-3.5 space-y-3 animate-fade-in">
                        {v.evidenceFile && (
                          <div className="flex items-center gap-2 text-xs font-mono text-foreground">
                            <FileCode2 className="h-3.5 w-3.5 text-primary shrink-0" />
                            <span className="font-semibold">{v.evidenceFile}</span>
                          </div>
                        )}

                        {v.evidenceSnippet ? (
                          <div className="relative rounded-md bg-neutral-950 p-3 font-mono text-xs text-emerald-400 overflow-x-auto border border-neutral-800">
                            <pre className="whitespace-pre">{v.evidenceSnippet}</pre>
                          </div>
                        ) : (
                          <p className="text-xs italic text-muted-foreground">
                            No matching code evidence snippet found in diff.
                          </p>
                        )}

                        {/* Developer Human-in-the-Loop Override Controls */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/40 text-xs">
                          <div className="flex items-center gap-2">
                            <UserCheck className="h-3.5 w-3.5 text-primary" />
                            <span className="font-medium text-foreground">Developer Ground-Truth Override:</span>
                          </div>

                          <Select
                            value={v.isUserOverridden ? v.status : "__DEFAULT__"}
                            onValueChange={(val) => handleOverrideStatus(v.reqId, val)}
                          >
                            <SelectTrigger className="h-8 w-44 text-xs bg-background">
                              <SelectValue placeholder="Override status…" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="covered">Mark as Covered</SelectItem>
                              <SelectItem value="partial">Mark as Partial</SelectItem>
                              <SelectItem value="missing">Mark as Missing</SelectItem>
                              <SelectItem value="unclear">Mark as Unclear</SelectItem>
                              {v.isUserOverridden && <SelectItem value="__RESET__">↺ Reset to AI Verdict</SelectItem>}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Changed Files Summary */}
          {brief.changedFilesSummary.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Changed Files in PR ({brief.changedFilesSummary.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-border/60">
                  {brief.changedFilesSummary.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 text-xs font-mono">
                      <div className="flex items-center gap-2 truncate">
                        <Code2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="truncate text-foreground font-medium">{file.filename}</span>
                        <span className="text-[10px] text-muted-foreground uppercase px-1.5 py-0.2 rounded bg-muted">
                          {file.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 font-bold">
                        <span className="text-success">+{file.additions}</span>
                        <span className="text-danger">-{file.deletions}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
