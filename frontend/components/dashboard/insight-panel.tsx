"use client";

import { CheckCircle2, Lightbulb, ShieldAlert, TrendingUp } from "lucide-react";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";

const icons = {
  emerald: TrendingUp,
  amber: ShieldAlert,
  violet: Lightbulb,
  sky: CheckCircle2,
};

export function InsightPanel() {
  const { analytics } = useDashboardData();
  const insights = analytics?.insights ?? [];

  return (
    <div className="glass-card rounded-[28px] p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">AI insights</p>
          <h3 className="text-xl font-semibold text-white">Recommended actions</h3>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-200 ring-1 ring-violet-400/20">
          <CheckCircle2 className="h-4 w-4" />
        </div>
      </div>

      <div className="space-y-3">
        {insights.length === 0 ? (
          <p className="text-sm text-slate-400">Insights appear after files are imported.</p>
        ) : (
          insights.map(({ title, detail, tone }, index) => {
            const Icon = icons[tone as keyof typeof icons] ?? Lightbulb;
            return (
              <div key={`${title}-${detail}-${index}`} className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
                <div className="mb-3 flex items-center gap-3">
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-xl ring-1 ${
                      tone === "emerald"
                        ? "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20"
                        : tone === "amber"
                          ? "bg-amber-500/10 text-amber-300 ring-amber-400/20"
                          : "bg-violet-500/10 text-violet-300 ring-violet-400/20"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <h4 className="text-base font-medium text-white">{title}</h4>
                </div>
                <p className="text-sm text-slate-300">{detail}</p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
