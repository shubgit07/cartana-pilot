"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Code2,
  FileDiff,
  GitPullRequest,
  Layers,
  ListChecks,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { CartanaLogo } from "@/components/layout/CartanaLogo";
import "./landing.css";

const navItems = [
  { label: "PR Reviewer", href: "#features" },
  { label: "Spec Audit", href: "#spec-audit" },
  { label: "Benchmarks", href: "#benchmarks" },
  { label: "Architecture", href: "#architecture" },
];

const sideItems = [
  { icon: "◉", label: "Audit Runs", active: true },
  { icon: "◇", label: "PR Verifier", active: false },
  { icon: "◌", label: "Requirements", active: false },
  { icon: "⌁", label: "Codebase Index", active: false },
];

const recentAudits = [
  { icon: "◐", label: "PR #104: Auth rate limiting", active: true },
  { icon: "◈", label: "PR #98: Vector chunking sync", active: false },
  { icon: "✦", label: "PR #87: LLM routing fallback", active: false },
  { icon: "◆", label: "PR #74: Neon PostgreSQL migration", active: false },
];

export function LandingPage() {
  return (
    <div className="landing-root">
      {/* Site Header */}
      <header className="landing-header">
        <nav className="landing-nav-shell" aria-label="Site navigation">
          <Link href="/" className="landing-brand">
            <span className="landing-brand-logo">
              <CartanaLogo className="size-4" />
            </span>
            <span>Cartana</span>
          </Link>

          <div className="landing-desktop-nav">
            {navItems.map((item) => (
              <a key={item.label} href={item.href}>
                {item.label}
              </a>
            ))}
          </div>

          <div className="landing-nav-actions">
            <a
              href="https://github.com/shubgit07/cartana-pilot"
              target="_blank"
              rel="noreferrer"
              className="landing-docs-link"
            >
              GitHub
            </a>
            <Link href="/projects" className="landing-open-app-btn">
              <span>Open app</span>
              <ArrowUpRight className="size-3.5" />
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main>
        <section className="landing-hero">
          <Link href="/projects" className="landing-badge">
            <span className="landing-badge-pill">New</span>
            <span>LangGraph PR Trust Verification & Drift Detection</span>
            <span className="arrow">↗</span>
          </Link>

          <h1>
            The spec-driven PR reviewer
            <br />
            <span className="gradient-text">for teams shipping with AI.</span>
          </h1>

          <div className="landing-hero-meta">
            <p>
              When AI generates code in seconds, human reviews become the bottleneck.
              Cartana cross-references pull requests against your actual feature specs
              with <b>verbatim evidence checking</b> and <b>zero hallucinations</b>.
            </p>
            <Link href="/projects">
              <b>Launch Cartana</b>
              <span className="arrow">→</span>
            </Link>
          </div>
        </section>

        {/* Product Preview Wrap */}
        <section className="landing-preview-wrap" aria-label="Cartana PR Trust Brief Preview">
          <div className="landing-ambient-glow" aria-hidden="true" />

          {/* Floating App Window */}
          <div className="landing-app-window">
            {/* Window Left Sidebar */}
            <aside className="landing-app-sidebar">
              <div className="landing-workspace-bar">
                <div className="landing-workspace-name">
                  <span className="landing-workspace-logo">◩</span>
                  <b>Cartana Copilot</b>
                </div>
                <Link
                  href="/projects"
                  title="Open Workspace"
                  className="size-6 grid place-items-center rounded-full text-muted-foreground hover:text-white"
                >
                  <ArrowUpRight className="size-3.5" />
                </Link>
              </div>

              <div className="landing-sidebar-list">
                {sideItems.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    className={item.active ? "active" : ""}
                  >
                    <span className="landing-mini-icon">{item.icon}</span>
                    {item.label}
                  </button>
                ))}
              </div>

              <p className="landing-sidebar-label">
                Workspace <span>›</span>
              </p>
              <div className="landing-sidebar-list">
                <button type="button">
                  <span className="landing-mini-icon">◒</span>Specifications
                </button>
                <button type="button">
                  <span className="landing-mini-icon">▰</span>Repository Index
                </button>
                <button type="button">
                  <span className="landing-mini-icon">•••</span>Benchmarking
                </button>
              </div>

              <p className="landing-sidebar-label">
                Recent PR Audits <span>›</span>
              </p>
              <div className="landing-sidebar-list">
                {recentAudits.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    className={item.active ? "active" : ""}
                  >
                    <span className="landing-mini-icon">{item.icon}</span>
                    <span className="truncate">{item.label}</span>
                  </button>
                ))}
              </div>
            </aside>

            {/* Window Main Issue / Audit Panel */}
            <section className="landing-issue-panel">
              <header className="landing-issue-toolbar">
                <div className="landing-issue-id">
                  <span className="landing-status-pill-pass">
                    <span className="landing-status-dot-green" />
                    Passed: High Trust
                  </span>
                  <b>PR #104</b>
                  <span className="hidden sm:inline">feat(auth): token rotation & rate limits</span>
                </div>

                <div className="landing-quick-actions">
                  <button type="button" title="Copy markdown comment">
                    <span>↗ Copy Comment</span>
                  </button>
                  <button type="button" title="View unified diff">
                    <span>▣ Diff</span>
                  </button>
                  <Link href="/projects" className="text-white hover:underline">
                    <span>Run live ↗</span>
                  </Link>
                </div>
              </header>

              <div className="landing-issue-body">
                {/* Main Copy */}
                <main className="landing-issue-copy">
                  <h2>PR Trust Report: High Trust (94% Coverage)</h2>
                  <p>
                    Audited against <b>Feature Brief v2</b>. 3 of 3 requirements verified
                    with concrete diff evidence. No security gaps or missing backend checks.
                  </p>

                  {/* Metrics Banner */}
                  <div className="landing-metrics-banner">
                    <div className="landing-metric-box">
                      <span className="landing-metric-label">Trust</span>
                      <span className="landing-metric-val green">High</span>
                    </div>
                    <div className="landing-metric-box">
                      <span className="landing-metric-label">Coverage</span>
                      <span className="landing-metric-val green">94%</span>
                    </div>
                    <div className="landing-metric-box">
                      <span className="landing-metric-label">Evidence Claims</span>
                      <span className="landing-metric-val blue">3 Verified</span>
                    </div>
                    <div className="landing-metric-box">
                      <span className="landing-metric-label">Hallucinations</span>
                      <span className="landing-metric-val">0</span>
                    </div>
                  </div>

                  {/* Requirements List */}
                  <div className="space-y-3">
                    {/* Requirement 1 */}
                    <div className="landing-req-card">
                      <div className="landing-req-header">
                        <span className="landing-req-title">[R1] Refresh Token Rotation</span>
                        <span className="landing-req-badge">Covered</span>
                      </div>
                      <p className="landing-req-desc">
                        Every refresh operation must issue a new pair and invalidate the old token family.
                      </p>
                      <div className="landing-diff-snippet">
                        <div className="landing-diff-file">apps/api-py/app/services/auth_service.py</div>
                        <div className="landing-diff-line add">+ def rotate_refresh_token(user_id: str, old_token: str) -&gt; TokenPair:</div>
                        <div className="landing-diff-line add">+     family = validate_token_family(old_token)</div>
                        <div className="landing-diff-line add">+     return issue_new_token_pair(user_id, family_id=family.id)</div>
                      </div>
                    </div>

                    {/* Requirement 2 */}
                    <div className="landing-req-card">
                      <div className="landing-req-header">
                        <span className="landing-req-title">[R2] Login Rate Limiting (5 req/min)</span>
                        <span className="landing-req-badge">Covered</span>
                      </div>
                      <p className="landing-req-desc">
                        Enforce bounded Redis rate limit on public login endpoint to protect against brute-force attacks.
                      </p>
                      <div className="landing-diff-snippet">
                        <div className="landing-diff-file">apps/api-py/app/api/routes/auth.py</div>
                        <div className="landing-diff-line add">+ @router.post(&quot;/login&quot;)</div>
                        <div className="landing-diff-line add">+ @limiter.limit(&quot;5/minute&quot;)</div>
                        <div className="landing-diff-line add">+ async def login(request: Request, body: LoginInput):</div>
                      </div>
                    </div>
                  </div>
                </main>

                {/* Right Properties Panel */}
                <aside className="landing-properties">
                  <div className="landing-prop-item">
                    <span className="label">Status</span>
                    <span className="landing-prop-pill text-emerald-400">● Verified</span>
                  </div>
                  <div className="landing-prop-item">
                    <span className="label">Trust Level</span>
                    <span className="value">High (94%)</span>
                  </div>
                  <div className="landing-prop-item">
                    <span className="label">Evidence Check</span>
                    <span className="value">100% Verbatim</span>
                  </div>
                  <div className="landing-prop-item">
                    <span className="label">Execution Engine</span>
                    <span className="value">LangGraph v1</span>
                  </div>
                  <div className="landing-prop-item">
                    <span className="label">Re-audit Cache</span>
                    <span className="value">&lt;10ms (0 tokens)</span>
                  </div>
                  <div className="landing-prop-item">
                    <span className="label">Branch</span>
                    <span className="value">feat/auth-v2</span>
                  </div>

                  <div className="pt-6">
                    <Link
                      href="/projects"
                      className="block w-full py-2 px-3 text-center rounded-lg bg-surface-raised border border-border text-foreground font-medium text-xs hover:bg-surface-hover transition-colors"
                    >
                      Audit Your Own PR →
                    </Link>
                  </div>
                </aside>
              </div>
            </section>
          </div>
        </section>

        {/* Features Pillars Grid */}
        <section id="features" className="landing-features-grid">
          <div className="landing-feature-card">
            <div className="landing-feature-icon">
              <ShieldCheck className="size-5" />
            </div>
            <h3>Deterministic Evidence Gate</h3>
            <p>
              Unlike generic LLM bots that hallucinate critiques, Cartana strictly verifies
              every cited code snippet against the real unified diff. Unverified claims are
              instantly downgraded.
            </p>
          </div>

          <div className="landing-feature-card">
            <div className="landing-feature-icon">
              <Zap className="size-5" />
            </div>
            <h3>Decomposed LangGraph Pipeline</h3>
            <p>
              A 3-stage state machine compresses diff tokens by ~70–80%, isolates code
              verification from risk analysis, and eliminates token truncation on large PRs.
            </p>
          </div>

          <div className="landing-feature-card">
            <div className="landing-feature-icon">
              <GitPullRequest className="size-5" />
            </div>
            <h3>Zero-Cost Re-Audits</h3>
            <p>
              SHA-256 content hashes of the spec and diff ensure re-verifying an unchanged
              pull request takes &lt;10ms and consumes zero LLM tokens.
            </p>
          </div>
        </section>

        {/* Bottom CTA Banner */}
        <section className="landing-cta-banner">
          <h2>Tired of reviewing AI slop manually?</h2>
          <p>
            Verify pull requests against your specifications with deterministic confidence.
            Try Cartana with your project today.
          </p>
          <Link href="/projects" className="landing-open-app-btn">
            <span>Enter Workspace</span>
            <ArrowUpRight className="size-4" />
          </Link>
        </section>
      </main>
    </div>
  );
}
