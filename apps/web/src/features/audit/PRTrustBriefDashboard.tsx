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
  Sparkles,
  UserCheck,
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
import { RepoVerifyPicker } from "./RepoVerifyPicker";
import { downloadFile, formatPRBriefAsGithubMarkdown } from "@/lib/formatPrBrief";
import type {
  PRTrustBrief,
  VerificationVerdictStatus,
} from "@cartana/shared";

type Props = {
  projectId: string;
  externalBrief?: PRTrustBrief | null;
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

/** OpenQodex-style verdict sentence: the whole report in one line, capped at 40ch. */
function buildVerdictSentence(
  score: number,
  trust: "high" | "medium" | "low",
  missing: number,
  unverified: number
): string {
  const parts: string[] = [];
  if (missing > 0) parts.push(`${missing} requirement${missing === 1 ? "" : "s"} missing`);
  if (unverified > 0) {
    parts.push(`${unverified} evidence claim${unverified === 1 ? "" : "s"} unverified`);
  }
  const head =
    parts.length > 0 ? `${trust === "high" ? "Passed" : "Flagged"}: ${parts.join(", ")}` : "Passed: no gaps";
  return `${head}, coverage ${score}%`;
}

/**
 * Renders an evidence snippet as real diff context: added lines tinted green,
 * removed lines red, on a mono table with tabular line numbers.
 */
function DiffExcerpt({ snippet }: { snippet: string }) {
  const lines = snippet.split("\n");
  return (
    <div className="overflow-hidden rounded-md border border-border/70">
      <table className="w-full border-collapse font-mono text-xs">
        <tbody>
          {lines.map((line, idx) => {
            const sign = line.startsWith("+") ? "+" : line.startsWith("-") ? "-" : " ";
            const tone =
              sign === "+"
                ? "bg-diff-add-bg text-diff-add-fg"
                : sign === "-"
                  ? "bg-diff-del-bg text-diff-del-fg"
                  : "text-foreground";
            return (
              <tr key={idx} className={tone}>
                <td className="w-10 select-none border-r border-border/50 px-2 text-right text-[10px] text-muted-foreground/60 tabular">
                  {idx + 1}
                </td>
                <td className="w-5 select-none px-1 text-center text-muted-foreground">{sign}</td>
                <td className="whitespace-pre px-2 py-0.5 leading-5">
                  {line.replace(/^[+-]/, "")}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function PRTrustBriefDashboard({ projectId, externalBrief = null }: Props) {
  const { brief, fromCache, verifying, error, verify, loadBrief } = useVerifyPR(projectId);
  const { toast } = useToast();

  React.useEffect(() => {
    if (externalBrief) loadBrief(externalBrief);
  }, [externalBrief, loadBrief]);

  const [copied, setCopied] = React.useState(false);
  const [inputTab, setInputTab] = React.useState<"paste_diff" | "github_pr" | "connected_repo">("paste_diff");
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
        title: "Copied to clipboard",
        description: "The GitHub comment is ready to paste into the PR review box.",
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
    } catch {
      toast({
        title: "Verification failed",
        description: error || "Failed to analyze the pull request diff.",
        variant: "destructive",
      });
    }
  };

  // ---- Human-in-the-loop effective verdicts (overrides win over AI) ----
  const effectiveVerdicts = React.useMemo(() => {
    if (!brief) return [];
    return brief.verdicts.map((v) => {
      const override = userOverrides[v.reqId];
      if (override) {
        return {
          ...v,
          status: override.status,
          rationale: `${v.rationale} (User ground-truth: ${override.rationale})`,
          isUserOverridden: true,
        };
      }
      return { ...v, isUserOverridden: false };
    });
  }, [brief, userOverrides]);

  // ---- Deterministic metrics (mirrors the backend evidence gate) ----
  const effectiveCovered = effectiveVerdicts.filter((v) => v.status === "covered").length;
  const effectivePartial = effectiveVerdicts.filter((v) => v.status === "partial").length;
  const effectiveMissing = effectiveVerdicts.filter((v) => v.status === "missing").length;

  // Evidence gate surface: claims the verifier could not find in the diff.
  const effectiveUnverified = effectiveVerdicts.filter(
    (v) => v.evidenceVerified === false
  ).length;

  const totalReqs = brief ? brief.totalRequirements : 0;
  const effectiveScore = totalReqs > 0
    ? Math.round(((effectiveCovered + 0.5 * effectivePartial) / totalReqs) * 100)
    : 0;

  const hasCriticalAlert = brief
    ? brief.riskAlerts.some((a) => a.severity === "critical")
    : false;
  const effectiveTrustLevel: "high" | "medium" | "low" =
    effectiveScore < 50 || hasCriticalAlert
      ? "low"
      : effectiveScore >= 80 && effectiveMissing === 0 && effectiveUnverified === 0
        ? "high"
        : "medium";

  const verdictSentence = brief
    ? buildVerdictSentence(effectiveScore, effectiveTrustLevel, effectiveMissing, effectiveUnverified)
    : "";

  // Requirement index for the sticky side nav.
  const reqIndex = React.useMemo(
    () =>
      effectiveVerdicts.map((v) => ({
        reqId: v.reqId,
        title: v.title,
        status: v.status,
      })),
    [effectiveVerdicts]
  );

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
              <button
                type="button"
                onClick={() => setInputTab("connected_repo")}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                  inputTab === "connected_repo"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <GitPullRequest className="h-3.5 w-3.5" />
                Connected Repo
              </button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleVerify} className="space-y-4">
            {inputTab === "connected_repo" ? (
              <RepoVerifyPicker
                projectId={projectId}
                verifying={verifying}
                onVerifyUrl={(url) =>
                  verify({
                    githubPrUrl: url,
                    specText: specText.trim() ? specText : undefined,
                  })
                }
              />
            ) : (
              <>
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
              </>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Incomplete report: shown when verification fails, e.g. the upstream
          patch fetch returns a 502. One honest card, no dead state. */}
      {error && !brief && (
        <section className="rounded-md border border-warning/40 bg-warning-soft/20 px-4 py-4">
          <p className="eyebrow text-warning">Report incomplete</p>
          <p className="mt-2 max-w-[70ch] text-sm leading-relaxed text-foreground">{error}</p>
          <p className="mt-1 max-w-[70ch] text-xs leading-relaxed text-muted-foreground">
            Nothing was verified. Check the diff or pull request URL and run the audit again.
          </p>
        </section>
      )}

      {/* Report: masthead + sticky verdict bar + body */}
      {brief && (
        <div className="space-y-6 animate-fade-in">
          {/* Masthead: wordmark + report kind, then the verdict sentence at 40ch */}
          <header className="border-b border-border pb-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <span className="font-mono text-xs text-muted-foreground">Cartana trust report</span>
              <span
                className={cn(
                  "font-mono text-xs uppercase tracking-[0.04em]",
                  effectiveTrustLevel === "high"
                    ? "text-success"
                    : effectiveTrustLevel === "medium"
                      ? "text-warning"
                      : "text-danger"
                )}
              >
                report complete
              </span>
            </div>

            <h1
              className={cn(
                "mt-3 max-w-[40ch] text-2xl font-semibold leading-tight tracking-tight",
                effectiveTrustLevel === "high"
                  ? "text-foreground"
                  : effectiveTrustLevel === "medium"
                    ? "text-warning"
                    : "text-danger"
              )}
            >
              {verdictSentence}
            </h1>

            {/* Meta grid: change id, size, threshold, generated */}
            <dl className="mt-5 grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
              <div>
                <dt className="eyebrow">Change</dt>
                <dd className="mt-1 font-mono text-xs text-foreground tabular">
                  {brief.id.slice(-12)}
                </dd>
              </div>
              <div>
                <dt className="eyebrow">Size</dt>
                <dd className="mt-1 font-mono text-xs text-foreground tabular">
                  {brief.changedFilesSummary.length} files
                </dd>
              </div>
              <div>
                <dt className="eyebrow">Block threshold</dt>
                <dd className="mt-1 font-mono text-xs text-foreground">low trust</dd>
              </div>
              <div>
                <dt className="eyebrow">Generated</dt>
                <dd className="mt-1 font-mono text-xs text-foreground tabular">
                  {new Date(brief.createdAt).toLocaleString()}
                </dd>
              </div>
            </dl>
          </header>

          {/* Sticky verdict bar: counts + jump links */}
          <div className="sticky top-0 z-10 -mx-1 flex flex-wrap items-center justify-between gap-3 border-b border-border bg-background/95 px-1 py-2.5 backdrop-blur">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-muted-foreground tabular">
              <span
                className={cn(
                  "font-semibold uppercase tracking-[0.04em]",
                  effectiveTrustLevel === "high"
                    ? "text-success"
                    : effectiveTrustLevel === "medium"
                      ? "text-warning"
                      : "text-danger"
                )}
              >
                {effectiveTrustLevel}
              </span>
              <span>
                {effectiveCovered} covered · {effectivePartial} partial · {effectiveMissing} missing
              </span>
              {effectiveUnverified > 0 && (
                <span className="text-danger">
                  {effectiveUnverified} unverified evidence
                </span>
              )}
              {Object.keys(userOverrides).length > 0 && (
                <span className="text-primary">
                  {Object.keys(userOverrides).length} override
                  {Object.keys(userOverrides).length === 1 ? "" : "s"}
                </span>
              )}
              {fromCache && <span className="text-primary">cached, 0 tokens</span>}
            </div>

            <nav className="flex items-center gap-4 text-2xs font-semibold uppercase tracking-[0.04em] text-muted-foreground">
              <a href="#report-summary" className="hover:text-foreground">Summary</a>
              <a href="#report-requirements" className="hover:text-foreground">Requirements</a>
              <a href="#report-alerts" className="hover:text-foreground">Alerts</a>
              <a href="#report-files" className="hover:text-foreground">Files</a>
            </nav>
          </div>

          {/* Summary prose, capped at 70ch */}
          <section id="report-summary" className="scroll-mt-header">
            <p className="max-w-[70ch] text-sm leading-relaxed text-foreground">
              {brief.summary}
            </p>
          </section>

          {/* Coverage strip: the evidence gate made visible */}
          <section className="rounded-md border border-border/70 bg-surface px-4 py-3">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
              <div className="flex items-baseline gap-2">
                <dt className="eyebrow">Requirements</dt>
                <dd className="font-mono text-xs text-foreground tabular">{totalReqs}</dd>
              </div>
              <div className="flex items-baseline gap-2">
                <dt className="eyebrow">Coverage</dt>
                <dd className="font-mono text-xs text-foreground tabular">{effectiveScore}%</dd>
              </div>
              <div className="flex items-baseline gap-2">
                <dt className="eyebrow">Evidence checked</dt>
                <dd className="font-mono text-xs text-foreground tabular">
                  {brief.evidenceVerifiedCount ?? 0}
                </dd>
              </div>
              <div className="flex items-baseline gap-2">
                <dt className="eyebrow">Not found in diff</dt>
                <dd
                  className={cn(
                    "font-mono text-xs tabular",
                    (brief.evidenceUnverifiedCount ?? 0) > 0 ? "text-danger" : "text-foreground"
                  )}
                >
                  {brief.evidenceUnverifiedCount ?? 0}
                </dd>
              </div>
            </dl>
          </section>

          {/* Export actions */}
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border pt-4">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyGithubComment}
              className="gap-2 text-xs"
            >
              {copied ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  Copied comment
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 text-primary" />
                  Copy as GitHub PR comment
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

          {/* Risk alerts */}
          {brief.riskAlerts.length > 0 && (
            <section id="report-alerts" className="scroll-mt-header">
              <div className="flex items-center gap-2 border-b border-border pb-2">
                <ShieldAlert className="h-4 w-4 text-danger" aria-hidden="true" />
                <h2 className="eyebrow text-foreground">Risk alerts ({brief.riskAlerts.length})</h2>
              </div>
              <ul className="divide-y divide-border/60">
                {brief.riskAlerts.map((alert, idx) => (
                  <li key={idx} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={alert.severity === "critical" ? "danger" : "secondary"}
                          className="px-1.5 py-0.5"
                        >
                          {alert.severity}
                        </Badge>
                        <span className="text-sm font-medium text-foreground">{alert.title}</span>
                      </div>
                      <p className="max-w-[70ch] text-xs leading-relaxed text-muted-foreground">
                        {alert.description}
                      </p>
                    </div>

                    {alert.affectedFiles && alert.affectedFiles.length > 0 && (
                      <div className="flex flex-wrap gap-1 shrink-0">
                        {alert.affectedFiles.map((file, fIdx) => (
                          <span
                            key={fIdx}
                            className="rounded-sm border border-border/60 bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                          >
                            {file}
                          </span>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Requirements: sticky index + per-requirement evidence */}
          <section id="report-requirements" className="scroll-mt-header">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <h2 className="eyebrow text-foreground">
                Requirements ({effectiveVerdicts.length})
              </h2>
              <span className="font-mono text-2xs text-muted-foreground tabular">
                {effectiveCovered}/{totalReqs} covered
              </span>
            </div>

            <div className="grid gap-6 pt-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
              {/* Sticky side index */}
              <nav className="hidden lg:block">
                <ul className="sticky top-16 space-y-1.5 border-l border-border pl-3">
                  {reqIndex.map((r) => (
                    <li key={r.reqId}>
                      <a
                        href={`#req-${r.reqId}`}
                        className="flex items-baseline gap-2 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <span className="font-mono text-foreground">{r.reqId}</span>
                        <span className="truncate">{r.title}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>

              {/* Verdict list */}
              <ol className="space-y-0 divide-y divide-border/60">
                {effectiveVerdicts.map((v, idx) => {
                const config = VERDICT_STYLES[v.status] || VERDICT_STYLES.unclear;
                const Icon = config.icon;
                const isExpanded = expandedReqs[v.reqId];

                return (
                  <li
                    key={v.reqId}
                    id={`req-${v.reqId}`}
                    className="scroll-mt-header py-4 transition-colors hover:bg-muted/10"
                  >
                    <div
                      onClick={() => toggleReq(v.reqId)}
                      className="flex cursor-pointer items-start justify-between gap-4 px-1"
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <button
                          type="button"
                          className="mt-0.5 text-muted-foreground"
                          aria-expanded={isExpanded}
                          aria-label={`Toggle evidence for ${v.reqId}`}
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </button>

                        <div className="space-y-1.5 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs text-muted-foreground tabular">
                              {idx + 1}.
                            </span>
                            <span className="font-mono text-xs font-semibold text-primary">
                              {v.reqId}
                            </span>
                            <span className="text-sm font-medium text-foreground">{v.title}</span>
                            {v.isUserOverridden && (
                              <Badge variant="outline" className="border-primary/50 px-1.5 py-0.5 text-primary">
                                <UserCheck className="mr-1 h-3 w-3 inline" />
                                user verified
                              </Badge>
                            )}
                          </div>

                          {/* Verdict / evidence / confidence rows, report style */}
                          <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-[6.5rem_minmax(0,1fr)]">
                            <dt className="eyebrow">Verdict</dt>
                            <dd>
                              <Badge className={cn("gap-1 px-1.5 py-0.5", config.badge)}>
                                <Icon className="h-3 w-3" />
                                {config.label}
                              </Badge>
                            </dd>

                            {v.evidenceFile && (
                              <>
                                <dt className="eyebrow">Evidence</dt>
                                <dd className="flex flex-wrap items-center gap-2 font-mono text-xs text-foreground">
                                  <FileCode2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                                  <span className="break-all">{v.evidenceFile}</span>
                                  {v.evidenceVerified === true && (
                                    <Badge variant="success" className="px-1.5 py-0.5">
                                      found in diff
                                    </Badge>
                                  )}
                                  {v.evidenceVerified === false && (
                                    <Badge variant="danger" className="px-1.5 py-0.5">
                                      not found in diff
                                    </Badge>
                                  )}
                                </dd>
                              </>
                            )}

                            <dt className="eyebrow">Why</dt>
                            <dd className="max-w-[70ch] text-xs leading-relaxed text-muted-foreground">
                              {v.rationale}
                            </dd>

                            <dt className="eyebrow">Confidence</dt>
                            <dd className="font-mono text-xs text-muted-foreground">{v.confidence}</dd>
                          </dl>
                        </div>
                      </div>
                    </div>

                    {/* Evidence diff excerpt + override controls */}
                    {isExpanded && (
                      <div className="mt-3 ml-7 space-y-3 pl-1 animate-fade-in">
                        {v.evidenceSnippet ? (
                          <DiffExcerpt snippet={v.evidenceSnippet} />
                        ) : (
                          <p className="text-xs italic text-muted-foreground">
                            No code evidence claimed for this verdict.
                          </p>
                        )}

                        {v.evidenceVerified === false && (
                          <p className="max-w-[70ch] rounded-md border border-danger/30 bg-danger-soft/20 px-3 py-2 text-xs leading-relaxed text-danger-soft-foreground">
                            This evidence could not be found in the supplied diff, so it does not
                            count toward coverage. Confirm or correct the verdict below.
                          </p>
                        )}

                        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3 text-xs">
                          <div className="flex items-center gap-2">
                            <UserCheck className="h-3.5 w-3.5 text-primary" />
                            <span className="font-medium text-foreground">Developer disposition</span>
                          </div>

                          <Select
                            value={v.isUserOverridden ? v.status : "__DEFAULT__"}
                            onValueChange={(val) => handleOverrideStatus(v.reqId, val)}
                          >
                            <SelectTrigger className="h-8 w-44 text-xs bg-background">
                              <SelectValue placeholder="Set verdict…" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="covered">Covered</SelectItem>
                              <SelectItem value="partial">Partial</SelectItem>
                              <SelectItem value="missing">Missing</SelectItem>
                              <SelectItem value="unclear">Unclear</SelectItem>
                              {v.isUserOverridden && (
                                <SelectItem value="__RESET__">Reset to AI verdict</SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
              </ol>
            </div>
          </section>

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
