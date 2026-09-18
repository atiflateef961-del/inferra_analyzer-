"use client";

import { useSyncExternalStore } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";

export function CategoryChart() {
  const { analytics } = useDashboardData();
  const data = analytics?.categories ?? [];
  const isMounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  return (
    <div className="glass-card h-[310px] p-5 sm:p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">Sales by category</p>
          <h3 className="text-xl font-semibold text-white">Top revenue streams</h3>
        </div>
      </div>

      {isMounted && data.length > 0 ? (
        <ResponsiveContainer width="100%" height="80%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="category" tickLine={false} axisLine={false} tick={{ fill: "#cbd5e1", fontSize: 12 }} />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: "#cbd5e1", fontSize: 12 }} />
            <Tooltip
              formatter={(value) => {
                const numericValue = Number(value ?? 0);
                return [`$${numericValue.toLocaleString()}`, "Sales"];
              }}
              contentStyle={{
                background: "rgba(15, 23, 42, 0.92)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "12px",
                color: "#f8fafc",
              }}
            />
            <Bar dataKey="sales" radius={[8, 8, 0, 0]} fill="#2dd4bf" />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-sm text-slate-400">Add a category or product column to chart revenue streams.</p>
      )}
    </div>
  );
}
