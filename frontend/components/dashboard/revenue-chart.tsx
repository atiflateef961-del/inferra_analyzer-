"use client";

import { useSyncExternalStore } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";
import { formatMoney } from "@/lib/api";

export function RevenueChart() {
  const { analytics } = useDashboardData();
  const data = analytics?.series ?? [];
  const total = analytics?.kpis.revenue ?? 0;
  const isMounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  return (
    <div className="glass-card h-[320px] p-5 sm:p-6">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-300">Revenue performance</p>
          <h3 className="text-xl font-semibold text-white">{formatMoney(total)}</h3>
        </div>
        <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-xs font-medium text-emerald-200">
          {analytics?.kpis.revenue_delta ?? "0.0%"}
        </span>
      </div>

      {isMounted && data.length > 0 ? (
        <ResponsiveContainer width="100%" height="80%">
          <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#34d399" stopOpacity={0.7} />
                <stop offset="95%" stopColor="#34d399" stopOpacity={0.04} />
              </linearGradient>
            </defs>
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
            <Area type="monotone" dataKey="revenue" stroke="#34d399" strokeWidth={3} fill="url(#revenueFill)" />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-sm text-slate-400">Upload a spreadsheet with month and revenue columns to chart performance.</p>
      )}
    </div>
  );
}
