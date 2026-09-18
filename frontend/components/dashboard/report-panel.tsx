"use client";

import { ArrowRight, FileText, Sparkles, TrendingUp } from "lucide-react";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";

const icons = {
  emerald: FileText,
  violet: Sparkles,
  sky: TrendingUp,
};

export function ReportPanel() {
  const { analytics } = useDashboardData();
  const reportCards = analytics?.reports ?? [];

  return (
    <div className="glass-card rounded-[28px] p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">Reports & AI</p>
          <h3 className="text-xl font-semibold text-white">Executive snapshot</h3>
        </div>
        <a
          href="#documents"
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/10"
        >
          View files
          <ArrowRight className="h-3.5 w-3.5" />
        </a>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {reportCards.length === 0 ? (
          <p className="text-sm text-slate-400">Reports populate from imported documents.</p>
        ) : (
          reportCards.map(({ title, description, value, accent }) => {
            const Icon = icons[accent as keyof typeof icons] ?? FileText;
            return (
              <div key={title} className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-xl ring-1 ${
                      accent === "emerald"
                        ? "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20"
                        : accent === "violet"
                          ? "bg-violet-500/10 text-violet-300 ring-violet-400/20"
                          : "bg-sky-500/10 text-sky-300 ring-sky-400/20"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="text-xs uppercase tracking-[0.18em] text-slate-400">Live</span>
                </div>

                <p className="text-lg font-semibold text-white">{value}</p>
                <h4 className="mt-2 text-base font-medium text-slate-100">{title}</h4>
                <p className="mt-2 text-sm text-slate-300">{description}</p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
