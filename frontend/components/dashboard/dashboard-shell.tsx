"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowUpRight,
  Bell,
  Briefcase,
  FileText,
  FolderKanban,
  LayoutGrid,
  MessageSquareText,
  Search,
  Sparkles,
  TrendingUp,
  Wallet,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { AnalyticsSummary } from "@/components/dashboard/analytics-summary";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { RevenueChart } from "@/components/dashboard/revenue-chart";
import { ProfitChart } from "@/components/dashboard/profit-chart";
import { CategoryChart } from "@/components/dashboard/category-chart";
import { ReportPanel } from "@/components/dashboard/report-panel";
import { UploadPanel } from "@/components/dashboard/upload-panel";
import { InsightPanel } from "@/components/dashboard/insight-panel";
import { DocumentTable } from "@/components/dashboard/document-table";
import { ChatPanel } from "@/components/dashboard/chat-panel";
import { DataMap } from "@/components/dashboard/data-map";
import { DayMood } from "@/components/dashboard/day-mood";
import { DashboardDataProvider, useDashboardData } from "@/components/dashboard/dashboard-data-provider";
import { formatMoney } from "@/lib/api";

const navItems = [
  { label: "Overview", icon: LayoutGrid, href: "#overview" },
  { label: "Revenue", icon: Wallet, href: "#revenue" },
  { label: "Expenses", icon: Briefcase, href: "#revenue" },
  { label: "Profit", icon: TrendingUp, href: "#profit" },
  { label: "Orders", icon: FolderKanban, href: "#documents" },
  { label: "Products", icon: FileText, href: "#categories" },
  { label: "Documents", icon: FileText, href: "#documents" },
  { label: "AI Insights", icon: Sparkles, href: "#insights" },
  { label: "Alerts", icon: AlertTriangle, href: "#alerts" },
  { label: "Reports", icon: MessageSquareText, href: "#reports" },
];

function DashboardWorkspace() {
  const { analytics, backendStatus, error, refresh, searchDocuments, loading } = useDashboardData();
  const kpis = analytics?.kpis;

  return (
    <div className="min-h-screen min-w-0 overflow-x-hidden px-4 py-5 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-[1840px] gap-5">
        <aside className="glass-sidebar hidden w-[250px] shrink-0 rounded-[28px] p-4 lg:flex lg:flex-col">
          <div className="mb-8 flex items-center gap-3 px-2 pt-2">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-violet-500 shadow-lg shadow-emerald-500/20">
              <Sparkles className="h-5 w-5 text-slate-950" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">AI business</p>
              <h1 className="text-lg font-semibold text-white">Inferra AI</h1>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map(({ label, icon: Icon, href }) => (
              <a
                key={label}
                href={href}
                className="flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left text-sm text-slate-300 transition-all hover:bg-white/5 hover:text-white"
              >
                <Icon className="h-4 w-4" />
                {label}
              </a>
            ))}
          </nav>

          <div className="mt-auto rounded-[24px] border border-violet-400/20 bg-violet-500/8 p-4">
            <div className="mb-3 flex items-center gap-2 text-violet-200">
              <Sparkles className="h-4 w-4" />
              <span className="text-sm font-medium">AI insights</span>
            </div>
            <p className="text-sm text-slate-300">
              {analytics?.insights.length
                ? `${analytics.insights.length} live insight${analytics.insights.length === 1 ? "" : "s"} from imported files.`
                : "Import files to generate workspace insights."}
            </p>
          </div>
        </aside>

        <main className="min-w-0 flex-1 rounded-[30px] border border-white/10 bg-slate-950/35 p-3 shadow-[0_30px_80px_rgba(2,6,23,0.7)] backdrop-blur-xl sm:p-4 lg:p-5">
          <header className="mb-6 grid min-w-0 gap-4 overflow-hidden rounded-[24px] border border-white/10 bg-white/[0.03] p-4 lg:grid-cols-[minmax(220px,1fr)_auto] lg:items-center">
            <div className="min-w-0">
              <p className="text-sm text-slate-400">Operations overview</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-white">Business command center</h2>
              {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}
            </div>

            <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center lg:justify-end">
              <span
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium ${
                  backendStatus === "connected"
                    ? "border-emerald-400/25 bg-emerald-500/10 text-emerald-200"
                    : backendStatus === "offline"
                      ? "border-red-400/25 bg-red-500/10 text-red-200"
                      : "border-white/10 bg-white/5 text-slate-300"
                }`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                Backend {backendStatus}
              </span>

              <div className="glass-input flex min-w-0 items-center gap-2 rounded-2xl px-3 py-2.5 text-slate-300">
                <Search className="h-4 w-4 text-slate-400" />
                <input
                  aria-label="Search dashboard"
                  placeholder="Search files"
                  onChange={(event) => void searchDocuments(event.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none sm:w-44"
                />
              </div>

              <button className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-200 transition hover:bg-white/10" aria-label="Notifications">
                <Bell className="h-4 w-4" />
              </button>

              <Button variant="default" className="rounded-2xl px-5" onPress={() => void refresh()} isDisabled={loading}>
                Analyze docs
              </Button>
            </div>
          </header>

          <div className="mb-4 flex gap-2 overflow-x-auto pb-1 lg:hidden">
            {navItems.map(({ label, icon: Icon, href }) => (
              <a
                key={label}
                href={href}
                className="flex shrink-0 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-300"
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </a>
            ))}
          </div>

          <motion.section
            id="overview"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4"
          >
            <KpiCard
              label="Total Revenue"
              value={formatMoney(kpis?.revenue ?? 0)}
              delta={kpis?.revenue_delta ?? "0.0%"}
              trend={kpis?.revenue_trend ?? "up"}
              icon={Wallet}
            />
            <KpiCard
              label="Total Expenses"
              value={formatMoney(kpis?.expenses ?? 0)}
              delta={kpis?.expense_delta ?? "0.0%"}
              trend={kpis?.expense_trend ?? "down"}
              icon={Briefcase}
            />
            <KpiCard
              label="Net Profit"
              value={formatMoney(kpis?.profit ?? 0)}
              delta={kpis?.profit_delta ?? "0.0%"}
              trend={kpis?.profit_trend ?? "up"}
              icon={TrendingUp}
            />
            <KpiCard
              label="Profit Margin"
              value={`${(kpis?.margin ?? 0).toFixed(1)}%`}
              delta={kpis?.margin_delta ?? "0.0%"}
              trend={kpis?.margin_trend ?? "up"}
              icon={ArrowUpRight}
            />
          </motion.section>

          <div className="mb-6">
            <AnalyticsSummary />
          </div>

          <DayMood />

          <section id="revenue" className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(0,0.95fr)]">
            <div className="min-w-0">
              <RevenueChart />
            </div>

            <div className="min-w-0 space-y-5">
              <div id="insights" className="glass-card rounded-[28px] p-5">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-300">AI analysis</p>
                    <h3 className="text-xl font-semibold text-white">
                      {(analytics?.headline_insights.length ?? 0) || 0} business insights
                    </h3>
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/20">
                    <Sparkles className="h-4 w-4" />
                  </div>
                </div>

                <div className="space-y-3">
                  {(analytics?.headline_insights.length ? analytics.headline_insights : ["Import files to generate live insights."]).map(
                    (insight, index) => (
                      <div key={`${insight}-${index}`} className="ai-insight-card rounded-2xl p-3">
                        <p className="text-sm text-slate-200">{insight}</p>
                      </div>
                    ),
                  )}
                </div>
              </div>

              <div id="alerts" className="glass-card rounded-[28px] p-5">
                <p className="text-sm text-slate-300">Review queue</p>
                <div className="mt-4 space-y-3">
                  {(analytics?.alerts.length ? analytics.alerts : [{ label: "No open issues", status: "Monitoring" }]).map((item, index) => (
                    <div key={`${item.label}-${item.status}-${index}`} className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/4 px-3 py-2.5">
                      <span className="text-sm text-slate-200">{item.label}</span>
                      <span className="rounded-full bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-200">
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section id="profit" className="mt-6 grid min-w-0 gap-5 xl:grid-cols-2">
            <div className="min-w-0">
              <ProfitChart />
            </div>
            <div id="categories" className="min-w-0">
              <CategoryChart />
            </div>
          </section>

          <DataMap />

          <div className="mt-6 grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
            <div className="min-w-0"><UploadPanel /></div>
            <div className="min-w-0"><InsightPanel /></div>
          </div>

          <div id="documents" className="mt-6 grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
            <div className="min-w-0"><DocumentTable /></div>
            <div className="min-w-0"><ChatPanel /></div>
          </div>

          <div id="reports" className="mt-6">
            <ReportPanel />
          </div>
        </main>
      </div>
    </div>
  );
}

export function DashboardShell() {
  const router = useRouter();
  const [hasUser, setHasUser] = useState(false);

  useEffect(() => {
    const authorizationCheck = window.setTimeout(() => {
      if (window.localStorage.getItem("inferra-local-user")?.trim()) {
        setHasUser(true);
      } else {
        router.replace("/login");
      }
    }, 0);

    return () => window.clearTimeout(authorizationCheck);
  }, [router]);

  if (!hasUser) {
    return null;
  }

  return (
    <DashboardDataProvider>
      <DashboardWorkspace />
    </DashboardDataProvider>
  );
}
