"use client";

import { useSyncExternalStore } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";

export function ProfitChart() {
  const { analytics } = useDashboardData();
  const data = analytics?.series ?? [];
  const isMounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  return (
    <div className="glass-card h-[310px] p-5 sm:p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">Profit trend</p>
          <h3 className="text-xl font-semibold text-white">Quarterly growth</h3>
        </div>
        <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-xs font-medium text-emerald-200">
          {analytics?.kpis.profit_delta ?? "0.0%"}
        </span>
      </div>

      {isMounted && data.length > 0 ? (
        <ResponsiveContainer width="100%" height="80%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: "#cbd5e1", fontSize: 12 }} />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: "#cbd5e1", fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "rgba(15, 23, 42, 0.92)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "12px",
                color: "#f8fafc",
              }}
            />
            <Line type="monotone" dataKey="profit" stroke="#a78bfa" strokeWidth={3} dot={{ r: 4, fill: "#a78bfa" }} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-sm text-slate-400">Profit trend appears after financial files are processed.</p>
      )}
    </div>
  );
}
