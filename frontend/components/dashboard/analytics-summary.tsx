"use client";

import { Activity, BellRing, FileText, ShieldCheck } from "lucide-react";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";

export function AnalyticsSummary() {
  const { analytics } = useDashboardData();
  const summary = analytics?.summary;
  const metrics = [
    { label: "Documents analyzed", value: String(summary?.documents_analyzed ?? 0), icon: FileText, tone: "emerald" },
    { label: "Alerts tracked", value: String(summary?.alerts_tracked ?? 0), icon: BellRing, tone: "amber" },
    { label: "System health", value: summary?.system_health ?? "Waiting", icon: ShieldCheck, tone: "sky" },
    { label: "AI signal", value: summary?.ai_signal ?? "Idle", icon: Activity, tone: "violet" },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map(({ label, value, icon: Icon, tone }) => (
        <div key={label} className="glass-card rounded-[24px] p-4">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-slate-300">{label}</p>
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-xl ring-1 ${
                tone === "emerald"
                  ? "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20"
                  : tone === "amber"
                    ? "bg-amber-500/10 text-amber-300 ring-amber-400/20"
                    : tone === "sky"
                      ? "bg-sky-500/10 text-sky-300 ring-sky-400/20"
                      : "bg-violet-500/10 text-violet-300 ring-violet-400/20"
              }`}
            >
              <Icon className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-semibold tracking-tight text-white">{value}</p>
        </div>
      ))}
    </div>
  );
}
